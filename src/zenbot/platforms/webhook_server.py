"""Lightweight webhook server for platforms that require HTTP endpoints.

Used by WhatsApp (mandatory) and Telegram (optional, alternative to polling).
Built on python-telegram-bot's built-in webhook support and a simple
asyncio HTTP handler for WhatsApp.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from zenbot.utils.logging import get_logger

logger = get_logger(__name__)


class WebhookServer:
    """Simple asyncio-based HTTP server for receiving webhooks.

    Handles WhatsApp webhook verification and message delivery.
    Can also serve a healthcheck endpoint.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        self._host = host
        self._port = port
        self._routes: dict[str, Callable[..., Coroutine[Any, Any, tuple[int, str]]]] = {}
        self._server: asyncio.Server | None = None

    def add_route(
        self,
        path: str,
        handler: Callable[..., Coroutine[Any, Any, tuple[int, str]]],
    ) -> None:
        """Register a handler for a path. Handler returns (status_code, body)."""
        self._routes[path] = handler

    async def start(self) -> None:
        """Start the webhook server."""
        self._server = await asyncio.start_server(
            self._handle_connection, self._host, self._port
        )
        logger.info("webhook_server_started", host=self._host, port=self._port)

    async def stop(self) -> None:
        """Stop the webhook server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("webhook_server_stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an incoming HTTP connection."""
        try:
            # Read request line
            request_line = await asyncio.wait_for(
                reader.readline(), timeout=10.0
            )
            if not request_line:
                writer.close()
                return

            request_str = request_line.decode(errors="replace").strip()
            parts = request_str.split(" ")
            if len(parts) < 2:
                await self._send_response(writer, 400, "Bad Request")
                return

            method = parts[0]
            path = parts[1].split("?")[0]
            query_string = parts[1].split("?")[1] if "?" in parts[1] else ""

            # Read headers
            headers: dict[str, str] = {}
            while True:
                header_line = await asyncio.wait_for(
                    reader.readline(), timeout=10.0
                )
                line = header_line.decode(errors="replace").strip()
                if not line:
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            # Read body if present
            body = ""
            content_length = int(headers.get("content-length", "0"))
            if content_length > 0:
                raw_body = await asyncio.wait_for(
                    reader.readexactly(content_length), timeout=10.0
                )
                body = raw_body.decode(errors="replace")

            # Route to handler
            handler = self._routes.get(path)
            if handler is None:
                await self._send_response(writer, 404, "Not Found")
                return

            status, response_body = await handler(
                method=method,
                path=path,
                query_string=query_string,
                headers=headers,
                body=body,
            )
            await self._send_response(writer, status, response_body)

        except TimeoutError:
            await self._send_response(writer, 408, "Request Timeout")
        except Exception as e:
            logger.error("webhook_handler_error", error=str(e))
            await self._send_response(writer, 500, "Internal Server Error")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    @staticmethod
    async def _send_response(
        writer: asyncio.StreamWriter, status: int, body: str
    ) -> None:
        """Send an HTTP response."""
        status_messages = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            408: "Request Timeout",
            500: "Internal Server Error",
        }
        status_msg = status_messages.get(status, "Unknown")
        response = (
            f"HTTP/1.1 {status} {status_msg}\r\n"
            f"Content-Type: text/plain\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )
        writer.write(response.encode())
        await writer.drain()


def parse_query_params(query_string: str) -> dict[str, str]:
    """Parse URL query parameters."""
    params: dict[str, str] = {}
    if not query_string:
        return params
    for pair in query_string.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            params[key] = value
    return params
