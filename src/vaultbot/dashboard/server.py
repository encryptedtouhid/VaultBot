"""Authenticated web dashboard with Server-Sent Events (SSE).

No websockets — uses SSE for real-time updates (one-way server push).
All endpoints require token-based authentication.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from vaultbot.core.healthcheck import HealthStatus
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DashboardConfig:
    """Configuration for the web dashboard."""

    host: str = "127.0.0.1"  # Localhost only by default
    port: int = 8082
    api_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    cors_origin: str = ""


@dataclass
class DashboardEvent:
    """An event to broadcast via SSE."""

    event_type: str  # e.g., "message", "status", "plugin"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_sse(self) -> str:
        """Format as an SSE message."""
        payload = json.dumps({"type": self.event_type, "data": self.data})
        return f"event: {self.event_type}\ndata: {payload}\n\n"


class SSEBroadcaster:
    """Manages SSE client connections and broadcasts events."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue[str]] = []

    def subscribe(self) -> asyncio.Queue[str]:
        """Create a new SSE subscription."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._queues.append(queue)
        logger.info("sse_client_connected", total_clients=len(self._queues))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        """Remove an SSE subscription."""
        self._queues = [q for q in self._queues if q is not queue]
        logger.info("sse_client_disconnected", total_clients=len(self._queues))

    async def broadcast(self, event: DashboardEvent) -> None:
        """Send an event to all connected SSE clients."""
        sse_data = event.to_sse()
        dead_queues = []
        for queue in self._queues:
            try:
                queue.put_nowait(sse_data)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        # Clean up unresponsive clients
        for q in dead_queues:
            self._queues = [x for x in self._queues if x is not q]

    @property
    def client_count(self) -> int:
        return len(self._queues)


class DashboardServer:
    """Lightweight authenticated dashboard with SSE streaming.

    Endpoints:
        GET  /dashboard/api/status   — bot health and stats
        GET  /dashboard/api/plugins  — list installed plugins
        GET  /dashboard/api/events   — SSE stream of real-time events
        POST /dashboard/api/plugins/{name}/toggle — enable/disable plugin

    All endpoints require: Authorization: Bearer <token>
    """

    def __init__(
        self,
        config: DashboardConfig,
        health_status: HealthStatus,
    ) -> None:
        self._config = config
        self._health = health_status
        self._broadcaster = SSEBroadcaster()
        self._server: asyncio.Server | None = None
        self._routes: dict[str, Callable[..., Coroutine[Any, Any, tuple[int, str, str]]]] = {}
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Register route handlers."""
        self._routes["GET /dashboard/api/status"] = self._handle_status
        self._routes["GET /dashboard/api/plugins"] = self._handle_plugins
        self._routes["GET /dashboard/api/events"] = self._handle_sse

    @property
    def broadcaster(self) -> SSEBroadcaster:
        return self._broadcaster

    async def start(self) -> None:
        """Start the dashboard server."""
        self._server = await asyncio.start_server(
            self._handle_connection,
            self._config.host,
            self._config.port,
        )
        logger.info(
            "dashboard_started",
            host=self._config.host,
            port=self._config.port,
        )

    async def stop(self) -> None:
        """Stop the dashboard server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("dashboard_stopped")

    def _authenticate(self, headers: dict[str, str]) -> bool:
        """Check the Authorization header."""
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return False
        token = auth[7:]
        return secrets.compare_digest(token, self._config.api_token)

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an incoming HTTP connection."""
        try:
            # Read request line
            request_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            request_str = request_line.decode(errors="replace").strip()
            parts = request_str.split(" ")
            if len(parts) < 2:
                await self._send(writer, 400, "text/plain", "Bad Request")
                return

            method = parts[0]
            path = parts[1].split("?")[0]

            # Read headers
            headers: dict[str, str] = {}
            while True:
                header_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
                line = header_line.decode(errors="replace").strip()
                if not line:
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            # Authenticate
            if not self._authenticate(headers):
                await self._send(writer, 401, "text/plain", "Unauthorized")
                return

            # CORS headers
            cors = self._config.cors_origin

            # Route
            route_key = f"{method} {path}"
            handler = self._routes.get(route_key)
            if handler is None:
                await self._send(writer, 404, "text/plain", "Not Found")
                return

            # SSE is special — long-lived connection
            if path == "/dashboard/api/events":
                await self._stream_sse(writer, cors)
                return

            status, content_type, body = await handler(headers=headers)
            await self._send(writer, status, content_type, body, cors=cors)

        except TimeoutError:
            pass
        except Exception as e:
            logger.error("dashboard_error", error=str(e))
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_status(self, **_: Any) -> tuple[int, str, str]:
        """Return bot status as JSON."""
        return 200, "application/json", json.dumps(self._health.to_dict())

    async def _handle_plugins(self, **_: Any) -> tuple[int, str, str]:
        """Return installed plugins as JSON."""
        from vaultbot.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        plugins = [
            {
                "name": e.manifest.name,
                "version": e.manifest.version,
                "description": e.manifest.description,
                "enabled": e.enabled,
                "author": e.manifest.author,
            }
            for e in registry.list_plugins()
        ]
        return 200, "application/json", json.dumps({"plugins": plugins})

    async def _stream_sse(
        self, writer: asyncio.StreamWriter, cors: str = ""
    ) -> None:
        """Stream SSE events to the client."""
        # Send SSE headers
        headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/event-stream\r\n"
            "Cache-Control: no-cache\r\n"
            "Connection: keep-alive\r\n"
        )
        if cors:
            headers += f"Access-Control-Allow-Origin: {cors}\r\n"
        headers += "\r\n"
        writer.write(headers.encode())
        await writer.drain()

        # Subscribe and stream events
        queue = self._broadcaster.subscribe()
        try:
            while True:
                sse_data = await queue.get()
                writer.write(sse_data.encode())
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            self._broadcaster.unsubscribe(queue)

    @staticmethod
    async def _send(
        writer: asyncio.StreamWriter,
        status: int,
        content_type: str,
        body: str,
        cors: str = "",
    ) -> None:
        """Send an HTTP response."""
        status_msgs = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 404: "Not Found"}
        msg = status_msgs.get(status, "Unknown")
        response = (
            f"HTTP/1.1 {status} {msg}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
        )
        if cors:
            response += f"Access-Control-Allow-Origin: {cors}\r\n"
        response += f"Connection: close\r\n\r\n{body}"
        writer.write(response.encode())
        await writer.drain()
