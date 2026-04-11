"""HTTP healthcheck server for container orchestration.

Provides /health and /ready endpoints for Kubernetes, Docker, etc.
Runs as a lightweight asyncio server alongside the bot.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HealthStatus:
    """Tracks the health of various bot components."""

    started_at: float = field(default_factory=time.time)
    platforms_connected: dict[str, bool] = field(default_factory=dict)
    llm_available: bool = False
    last_message_at: float = 0.0

    @property
    def is_healthy(self) -> bool:
        """Bot is healthy if at least one platform is connected."""
        return any(self.platforms_connected.values())

    @property
    def is_ready(self) -> bool:
        """Bot is ready if healthy and LLM is available."""
        return self.is_healthy and self.llm_available

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.started_at

    def to_dict(self) -> dict[str, object]:
        return {
            "healthy": self.is_healthy,
            "ready": self.is_ready,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "platforms": self.platforms_connected,
            "llm_available": self.llm_available,
            "last_message_at": self.last_message_at,
        }


class HealthcheckServer:
    """Simple HTTP healthcheck server for container orchestration."""

    def __init__(
        self,
        status: HealthStatus,
        host: str = "0.0.0.0",
        port: int = 8081,
    ) -> None:
        self._status = status
        self._host = host
        self._port = port
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        """Start the healthcheck server."""
        self._server = await asyncio.start_server(
            self._handle, self._host, self._port
        )
        logger.info("healthcheck_started", host=self._host, port=self._port)

    async def stop(self) -> None:
        """Stop the healthcheck server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle healthcheck HTTP requests."""
        try:
            request_line = await asyncio.wait_for(
                reader.readline(), timeout=5.0
            )
            request_str = request_line.decode(errors="replace").strip()
            parts = request_str.split(" ")
            path = parts[1] if len(parts) >= 2 else "/"

            # Drain remaining headers
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=5.0)
                if line == b"\r\n" or not line:
                    break

            import json

            if path == "/health":
                status_code = 200 if self._status.is_healthy else 503
                body = json.dumps(self._status.to_dict())
            elif path == "/ready":
                status_code = 200 if self._status.is_ready else 503
                body = json.dumps(self._status.to_dict())
            else:
                status_code = 404
                body = "Not Found"

            status_text = "OK" if status_code == 200 else "Service Unavailable"
            if status_code == 404:
                status_text = "Not Found"

            response = (
                f"HTTP/1.1 {status_code} {status_text}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
                f"{body}"
            )
            writer.write(response.encode())
            await writer.drain()

        except Exception as e:
            logger.error("healthcheck_error", error=str(e))
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
