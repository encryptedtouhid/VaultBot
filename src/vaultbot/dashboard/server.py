"""Authenticated web dashboard with Server-Sent Events (SSE).

No websockets — uses SSE for real-time updates (one-way server push).
All API endpoints require token-based authentication.
Serves a full SPA from static files with REST API backend.
"""

from __future__ import annotations

import asyncio
import importlib.resources
import json
import mimetypes
import secrets
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from vaultbot.core.healthcheck import HealthStatus
from vaultbot.dashboard.api import DashboardAPI, DashboardContext
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Maximum request body size (64 KB)
_MAX_BODY_SIZE = 65536


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
    """Full-featured authenticated dashboard with REST API and SSE streaming.

    Endpoints:
        GET  /dashboard                         — serve SPA HTML
        GET  /dashboard/static/<file>           — serve static CSS/JS
        GET  /dashboard/api/status              — bot health and stats
        GET  /dashboard/api/events              — SSE stream of real-time events
        GET  /dashboard/api/config              — current config
        PUT  /dashboard/api/config              — update config
        GET  /dashboard/api/platforms           — platform status
        PUT  /dashboard/api/platforms/<name>    — toggle platform
        GET  /dashboard/api/llm                 — LLM config
        PUT  /dashboard/api/llm                 — update LLM
        GET  /dashboard/api/allowlist           — list users
        POST /dashboard/api/allowlist           — add user
        DELETE /dashboard/api/allowlist         — remove user
        GET  /dashboard/api/plugins             — list plugins
        POST /dashboard/api/plugins/<n>/enable  — enable plugin
        POST /dashboard/api/plugins/<n>/disable — disable plugin
        POST /dashboard/api/plugins/<n>/uninstall — uninstall plugin
        GET  /dashboard/api/teams               — list teams
        POST /dashboard/api/teams               — create team
        DELETE /dashboard/api/teams/<name>      — delete team
        POST /dashboard/api/teams/<n>/members   — add member
        DELETE /dashboard/api/teams/<n>/members — remove member
        GET  /dashboard/api/credentials         — credential status
        POST /dashboard/api/credentials/<key>   — set credential
        DELETE /dashboard/api/credentials/<key> — delete credential
        GET  /dashboard/api/audit               — recent audit events
        GET  /dashboard/api/ratelimit           — rate limit config
        PUT  /dashboard/api/ratelimit           — update rate limits

    All API endpoints require: Authorization: Bearer <token>
    """

    def __init__(
        self,
        config: DashboardConfig,
        health_status: HealthStatus,
        context: DashboardContext | None = None,
    ) -> None:
        self._config = config
        self._health = health_status
        self._broadcaster = SSEBroadcaster()
        self._server: asyncio.Server | None = None
        self._api = DashboardAPI(context) if context else None
        self._static_dir = importlib.resources.files("vaultbot.dashboard") / "static"

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

    def _authenticate(self, headers: dict[str, str], query_token: str = "") -> bool:
        """Check the Authorization header or query param token."""
        auth = headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            if secrets.compare_digest(token, self._config.api_token):
                return True
        if query_token and secrets.compare_digest(query_token, self._config.api_token):
            return True
        return False

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
            raw_path = parts[1]
            path = raw_path.split("?")[0]

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

            # Parse query string
            query_string = raw_path.split("?")[1] if "?" in raw_path else ""
            query_params: dict[str, str] = {}
            for pair in query_string.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query_params[k] = v

            # Read request body for POST/PUT/DELETE
            body_bytes = b""
            content_length = int(headers.get("content-length", "0"))
            if content_length > 0:
                if content_length > _MAX_BODY_SIZE:
                    await self._send(writer, 413, "text/plain", "Request body too large")
                    return
                body_bytes = await asyncio.wait_for(
                    reader.readexactly(content_length), timeout=10.0
                )

            # Handle CORS preflight
            if method == "OPTIONS":
                await self._send_cors_preflight(writer)
                return

            # Routes that don't need auth
            if method == "GET" and path == "/dashboard":
                await self._handle_dashboard_page(writer)
                return

            if method == "GET" and path.startswith("/dashboard/static/"):
                await self._handle_static_file(writer, path)
                return

            # All other routes require auth
            query_token = query_params.get("token", "")
            if not self._authenticate(headers, query_token):
                await self._send(writer, 401, "application/json", '{"error":"Unauthorized"}')
                return

            # SSE endpoint (long-lived)
            if method == "GET" and path == "/dashboard/api/events":
                await self._stream_sse(writer)
                return

            # Route to handler
            status, content_type, body = await self._route(method, path, body_bytes, query_params)
            cors = self._config.cors_origin
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

    async def _route(
        self,
        method: str,
        path: str,
        body_bytes: bytes,
        query_params: dict[str, str],
    ) -> tuple[int, str, str]:
        """Route request to the appropriate handler."""
        body: dict[str, Any] = {}
        if body_bytes:
            try:
                body = json.loads(body_bytes)
            except json.JSONDecodeError:
                return 400, "application/json", '{"error":"Invalid JSON"}'

        # Split path into segments: /dashboard/api/...
        segments = [s for s in path.split("/") if s]
        # segments[0] = "dashboard", segments[1] = "api", segments[2] = resource, ...

        if len(segments) < 3 or segments[0] != "dashboard" or segments[1] != "api":
            return 404, "application/json", '{"error":"Not Found"}'

        resource = segments[2]

        # --- Status ---
        if resource == "status" and method == "GET":
            return 200, "application/json", json.dumps(self._health.to_dict())

        # All remaining routes need the API layer
        if self._api is None:
            return 503, "application/json", '{"error":"Dashboard API not initialized"}'

        # --- Config ---
        if resource == "config":
            if method == "GET":
                status, data = await self._api.get_config()
                return status, "application/json", json.dumps(data)
            if method == "PUT":
                status, data = await self._api.update_config(body)
                return status, "application/json", json.dumps(data)

        # --- Platforms ---
        if resource == "platforms":
            if method == "GET" and len(segments) == 3:
                status, data = await self._api.get_platforms()
                return status, "application/json", json.dumps(data)
            if method == "PUT" and len(segments) == 4:
                platform_name = segments[3]
                status, data = await self._api.update_platform(platform_name, body)
                return status, "application/json", json.dumps(data)

        # --- LLM ---
        if resource == "llm":
            if method == "GET":
                status, data = await self._api.get_llm()
                return status, "application/json", json.dumps(data)
            if method == "PUT":
                status, data = await self._api.update_llm(body)
                return status, "application/json", json.dumps(data)

        # --- Allowlist ---
        if resource == "allowlist":
            if method == "GET":
                status, data = await self._api.get_allowlist()
                return status, "application/json", json.dumps(data)
            if method == "POST":
                status, data = await self._api.add_allowlist_entry(body)
                return status, "application/json", json.dumps(data)
            if method == "DELETE":
                status, data = await self._api.remove_allowlist_entry(body)
                return status, "application/json", json.dumps(data)

        # --- Plugins ---
        if resource == "plugins":
            if method == "GET" and len(segments) == 3:
                status, data = await self._api.get_plugins()
                return status, "application/json", json.dumps(data)
            if method == "POST" and len(segments) == 5:
                plugin_name = segments[3]
                action = segments[4]
                if action == "enable":
                    status, data = await self._api.enable_plugin(plugin_name)
                    return status, "application/json", json.dumps(data)
                if action == "disable":
                    status, data = await self._api.disable_plugin(plugin_name)
                    return status, "application/json", json.dumps(data)
                if action == "uninstall":
                    status, data = await self._api.uninstall_plugin(plugin_name)
                    return status, "application/json", json.dumps(data)

        # --- Teams ---
        if resource == "teams":
            if method == "GET" and len(segments) == 3:
                status, data = await self._api.get_teams()
                return status, "application/json", json.dumps(data)
            if method == "POST" and len(segments) == 3:
                status, data = await self._api.create_team(body)
                return status, "application/json", json.dumps(data)
            if method == "DELETE" and len(segments) == 4:
                status, data = await self._api.delete_team(segments[3])
                return status, "application/json", json.dumps(data)
            if method == "POST" and len(segments) == 5 and segments[4] == "members":
                status, data = await self._api.add_team_member(segments[3], body)
                return status, "application/json", json.dumps(data)
            if method == "DELETE" and len(segments) == 5 and segments[4] == "members":
                status, data = await self._api.remove_team_member(segments[3], body)
                return status, "application/json", json.dumps(data)

        # --- Credentials ---
        if resource == "credentials":
            if method == "GET" and len(segments) == 3:
                status, data = await self._api.get_credentials()
                return status, "application/json", json.dumps(data)
            if method == "POST" and len(segments) == 4:
                status, data = await self._api.set_credential(segments[3], body)
                return status, "application/json", json.dumps(data)
            if method == "DELETE" and len(segments) == 4:
                status, data = await self._api.delete_credential(segments[3])
                return status, "application/json", json.dumps(data)

        # --- Audit ---
        if resource == "audit" and method == "GET":
            limit = int(query_params.get("limit", "50"))
            event_type = query_params.get("type")
            status, data = await self._api.get_audit(limit=limit, event_type=event_type)
            return status, "application/json", json.dumps(data)

        # --- Rate Limit ---
        if resource == "ratelimit":
            if method == "GET":
                status, data = await self._api.get_ratelimit()
                return status, "application/json", json.dumps(data)
            if method == "PUT":
                status, data = await self._api.update_ratelimit(body)
                return status, "application/json", json.dumps(data)

        return 404, "application/json", '{"error":"Not Found"}'

    async def _handle_dashboard_page(self, writer: asyncio.StreamWriter) -> None:
        """Serve the SPA HTML with token injected."""
        try:
            html_path = self._static_dir / "index.html"
            html = html_path.read_text()
            html = html.replace("{{TOKEN}}", self._config.api_token)
            html = html.replace("{{PORT}}", str(self._config.port))
            await self._send(writer, 200, "text/html", html)
        except Exception as e:
            logger.error("dashboard_page_error", error=str(e))
            await self._send(writer, 500, "text/plain", "Internal Server Error")

    async def _handle_static_file(self, writer: asyncio.StreamWriter, path: str) -> None:
        """Serve a static file (CSS, JS)."""
        # Extract filename from /dashboard/static/<filename>
        filename = path.split("/dashboard/static/", 1)[-1]

        # Prevent path traversal
        if ".." in filename or "/" in filename:
            await self._send(writer, 403, "text/plain", "Forbidden")
            return

        try:
            file_path = self._static_dir / filename
            content = file_path.read_text()
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            await self._send(writer, 200, content_type, content)
        except FileNotFoundError:
            await self._send(writer, 404, "text/plain", "Not Found")

    async def _stream_sse(self, writer: asyncio.StreamWriter) -> None:
        """Stream SSE events to the client."""
        cors = self._config.cors_origin
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

    async def _send_cors_preflight(self, writer: asyncio.StreamWriter) -> None:
        """Handle CORS preflight OPTIONS request."""
        cors = self._config.cors_origin or "*"
        response = (
            "HTTP/1.1 204 No Content\r\n"
            f"Access-Control-Allow-Origin: {cors}\r\n"
            "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Authorization, Content-Type\r\n"
            "Access-Control-Max-Age: 86400\r\n"
            "Connection: close\r\n\r\n"
        )
        writer.write(response.encode())
        await writer.drain()

    @staticmethod
    async def _send(
        writer: asyncio.StreamWriter,
        status: int,
        content_type: str,
        body: str,
        cors: str = "",
    ) -> None:
        """Send an HTTP response."""
        status_msgs = {
            200: "OK",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            413: "Payload Too Large",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }
        msg = status_msgs.get(status, "Unknown")
        body_bytes = body.encode()
        response = (
            f"HTTP/1.1 {status} {msg}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
        )
        if cors:
            response += f"Access-Control-Allow-Origin: {cors}\r\n"
        response += "Connection: close\r\n\r\n"
        writer.write(response.encode() + body_bytes)
        await writer.drain()
