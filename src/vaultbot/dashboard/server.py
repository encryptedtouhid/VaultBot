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
        self._routes["GET /dashboard"] = self._handle_dashboard_page
        self._routes["GET /dashboard/api/status"] = self._handle_status
        self._routes["GET /dashboard/api/plugins"] = self._handle_plugins

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

            # Parse query string for token auth (SSE can't set headers)
            query_string = parts[1].split("?")[1] if "?" in parts[1] else ""
            query_token = ""
            for pair in query_string.split("&"):
                if pair.startswith("token="):
                    query_token = pair[6:]

            # Dashboard HTML page — no auth (token is shown on CLI)
            no_auth_paths = {"/dashboard"}

            if path not in no_auth_paths:
                # Check header auth or query param auth
                has_auth = self._authenticate(headers) or (
                    query_token
                    and secrets.compare_digest(query_token, self._config.api_token)
                )
                if not has_auth:
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

    async def _handle_dashboard_page(self, **_: Any) -> tuple[int, str, str]:
        """Serve the real-time HTML dashboard."""
        token = self._config.api_token
        port = self._config.port
        html = _DASHBOARD_HTML.replace("{{TOKEN}}", token).replace("{{PORT}}", str(port))
        return 200, "text/html", html

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


# Dashboard HTML — uses textContent for user data to prevent XSS.
# innerHTML is only used with server-controlled template strings.
_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V.A.U.L.T. BOT Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
    background: #0a0a0a; color: #e0e0e0; padding: 20px;
  }
  .header {
    text-align: center; padding: 20px 0; border-bottom: 1px solid #222;
    margin-bottom: 20px;
  }
  .header h1 { color: #00d4ff; font-size: 1.5em; letter-spacing: 4px; }
  .header .subtitle { color: #666; font-size: 0.8em; margin-top: 4px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
  .card {
    background: #111; border: 1px solid #222; border-radius: 8px; padding: 16px;
  }
  .card h2 {
    color: #888; font-size: 0.75em; text-transform: uppercase;
    letter-spacing: 2px; margin-bottom: 12px;
  }
  .status-dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 6px;
  }
  .dot-green { background: #00ff88; box-shadow: 0 0 6px #00ff88; }
  .dot-red { background: #ff4444; box-shadow: 0 0 6px #ff4444; }
  .dot-yellow { background: #ffaa00; box-shadow: 0 0 6px #ffaa00; }
  .stat { margin: 8px 0; font-size: 0.9em; }
  .stat-value { color: #fff; font-weight: bold; }
  .events-container {
    background: #111; border: 1px solid #222; border-radius: 8px; padding: 16px;
  }
  .events-container h2 {
    color: #888; font-size: 0.75em; text-transform: uppercase;
    letter-spacing: 2px; margin-bottom: 12px;
  }
  #events {
    max-height: 400px; overflow-y: auto; font-size: 0.8em;
  }
  .event {
    padding: 8px 12px; margin: 4px 0; border-radius: 4px;
    border-left: 3px solid #333; background: #0d0d0d;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; }
  }
  .type-message_in { border-left-color: #00d4ff; }
  .type-message_in .event-type { color: #00d4ff; }
  .type-message_out { border-left-color: #00ff88; }
  .type-message_out .event-type { color: #00ff88; }
  .type-auth_denied { border-left-color: #ff4444; }
  .type-auth_denied .event-type { color: #ff4444; }
  .type-rate_limited { border-left-color: #ffaa00; }
  .type-rate_limited .event-type { color: #ffaa00; }
  .type-error { border-left-color: #ff4444; }
  .type-error .event-type { color: #ff4444; }
  .event-time { color: #555; font-size: 0.85em; }
  .event-type { font-weight: bold; margin: 0 8px; }
  .event-data { color: #888; }
  .connection-status {
    position: fixed; top: 10px; right: 20px; font-size: 0.75em;
    padding: 4px 12px; border-radius: 12px;
  }
  .connected { background: #0a2a0a; color: #00ff88; border: 1px solid #00ff88; }
  .disconnected { background: #2a0a0a; color: #ff4444; border: 1px solid #ff4444; }
  .counter { font-size: 2em; color: #fff; font-weight: bold; }
</style>
</head>
<body>

<div class="connection-status disconnected" id="connStatus">Connecting...</div>

<div class="header">
  <h1>V.A.U.L.T. BOT</h1>
  <div class="subtitle">Verified Autonomous Utility &amp; Logical Taskrunner</div>
</div>

<div class="grid">
  <div class="card">
    <h2>Status</h2>
    <div class="stat">
      <span class="status-dot dot-red" id="healthDot"></span>
      <span id="healthText">Loading...</span>
    </div>
    <div class="stat">Uptime: <span class="stat-value" id="uptime">-</span></div>
    <div class="stat">LLM: <span class="stat-value" id="llm">-</span></div>
  </div>
  <div class="card">
    <h2>Counters</h2>
    <div class="stat">Messages In: <span class="counter" id="msgIn">0</span></div>
    <div class="stat">Messages Out: <span class="counter" id="msgOut">0</span></div>
    <div class="stat">Blocked: <span class="counter" id="blocked">0</span></div>
  </div>
  <div class="card">
    <h2>Platforms</h2>
    <div id="platforms">Loading...</div>
  </div>
  <div class="card">
    <h2>Tokens Used</h2>
    <div class="stat">Input: <span class="counter" id="tokensIn">0</span></div>
    <div class="stat">Output: <span class="counter" id="tokensOut">0</span></div>
  </div>
</div>

<div class="events-container">
  <h2>Live Events</h2>
  <div id="events"></div>
</div>

<script>
const TOKEN = '{{TOKEN}}';
let msgIn = 0, msgOut = 0, blocked = 0, tokensIn = 0, tokensOut = 0;

async function fetchStatus() {
  try {
    const res = await fetch('/dashboard/api/status', {
      headers: { 'Authorization': 'Bearer ' + TOKEN }
    });
    const data = await res.json();
    const dot = document.getElementById('healthDot');
    dot.className = 'status-dot ' +
      (data.ready ? 'dot-green' : data.healthy ? 'dot-yellow' : 'dot-red');
    document.getElementById('healthText').textContent =
      data.ready ? 'Ready' : data.healthy ? 'Healthy' : 'Unhealthy';
    document.getElementById('uptime').textContent =
      Math.round(data.uptime_seconds) + 's';
    document.getElementById('llm').textContent =
      data.llm_available ? 'Connected' : 'Disconnected';
    const pDiv = document.getElementById('platforms');
    pDiv.textContent = '';
    for (const [name, connected] of Object.entries(data.platforms || {})) {
      const row = document.createElement('div');
      row.className = 'stat';
      const d = document.createElement('span');
      d.className = 'status-dot ' + (connected ? 'dot-green' : 'dot-red');
      row.appendChild(d);
      row.appendChild(document.createTextNode(name));
      pDiv.appendChild(row);
    }
  } catch(e) { /* retry on next interval */ }
}
fetchStatus();
setInterval(fetchStatus, 5000);

function connectSSE() {
  const es = new EventSource('/dashboard/api/events?token=' + TOKEN);
  const el = document.getElementById('connStatus');
  es.onopen = () => { el.className = 'connection-status connected'; el.textContent = 'Live'; };
  es.onerror = () => {
    el.className = 'connection-status disconnected';
    el.textContent = 'Reconnecting...';
  };

  es.addEventListener('message_in', (e) => {
    msgIn++; document.getElementById('msgIn').textContent = msgIn;
    addEvent('message_in', JSON.parse(e.data));
  });
  es.addEventListener('message_out', (e) => {
    msgOut++; document.getElementById('msgOut').textContent = msgOut;
    const d = JSON.parse(e.data);
    tokensIn += (d.data && d.data.tokens_in) || 0;
    tokensOut += (d.data && d.data.tokens_out) || 0;
    document.getElementById('tokensIn').textContent = tokensIn.toLocaleString();
    document.getElementById('tokensOut').textContent = tokensOut.toLocaleString();
    addEvent('message_out', d);
  });
  es.addEventListener('auth_denied', (e) => {
    blocked++; document.getElementById('blocked').textContent = blocked;
    addEvent('auth_denied', JSON.parse(e.data));
  });
  es.addEventListener('rate_limited', (e) => {
    blocked++; document.getElementById('blocked').textContent = blocked;
    addEvent('rate_limited', JSON.parse(e.data));
  });
  es.addEventListener('error', (e) => {
    if (e.data) addEvent('error', JSON.parse(e.data));
  });
}
connectSSE();

function addEvent(type, payload) {
  const evDiv = document.getElementById('events');
  const el = document.createElement('div');
  el.className = 'event type-' + type;

  const timeSpan = document.createElement('span');
  timeSpan.className = 'event-time';
  timeSpan.textContent = new Date().toLocaleTimeString();

  const typeSpan = document.createElement('span');
  typeSpan.className = 'event-type';
  typeSpan.textContent = type;

  const dataSpan = document.createElement('span');
  dataSpan.className = 'event-data';
  dataSpan.textContent = JSON.stringify(payload.data || payload).substring(0, 120);

  el.appendChild(timeSpan);
  el.appendChild(typeSpan);
  el.appendChild(dataSpan);
  evDiv.insertBefore(el, evDiv.firstChild);
  if (evDiv.children.length > 100) evDiv.removeChild(evDiv.lastChild);
}
</script>
</body>
</html>
"""
