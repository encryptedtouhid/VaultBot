"""Mattermost messaging platform adapter.

Implements an async Mattermost client using the REST API v4 and WebSocket
event stream via ``httpx`` and ``websockets``.  Supports personal access
token and bot account authentication, channel/direct message handling,
and real-time event streaming.

No third-party Mattermost SDK is required — the adapter speaks the
Mattermost REST + WebSocket APIs directly.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Mattermost API v4 paths
_ME = "/api/v4/users/me"
_POSTS = "/api/v4/posts"
_CHANNELS = "/api/v4/channels/{channel_id}"
_WS = "/api/v4/websocket"


class MattermostAdapter:
    """Mattermost bot adapter using REST API v4 + WebSocket events.

    Parameters
    ----------
    url:
        Full URL of the Mattermost server (e.g. ``https://chat.example.com``).
    token:
        Personal access token or bot token.
    """

    def __init__(
        self,
        *,
        url: str,
        token: str,
    ) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._user_id: str = ""
        self._client: httpx.AsyncClient | None = None
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._connected = False
        self._ws_task: asyncio.Task[None] | None = None
        self._ws_seq: int = 1

    # ------------------------------------------------------------------
    # PlatformAdapter protocol
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "mattermost"

    async def connect(self) -> None:
        """Authenticate and start the WebSocket event stream."""
        self._client = httpx.AsyncClient(timeout=30.0)

        # Resolve own user ID
        resp = await self._client.get(
            f"{self._url}{_ME}",
            headers=self._auth_headers(),
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Mattermost auth failed ({resp.status_code}): {resp.text[:200]}"
            )
        self._user_id = resp.json().get("id", "")

        # Start WebSocket listener
        self._ws_task = asyncio.create_task(self._ws_loop())
        self._connected = True
        logger.info("mattermost_connected", url=self._url, user_id=self._user_id)

    async def disconnect(self) -> None:
        """Stop the WebSocket listener and close the HTTP client."""
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.aclose()
            self._client = None

        self._connected = False
        logger.info("mattermost_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from Mattermost."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a message to a Mattermost channel."""
        if not self._client:
            raise RuntimeError("Mattermost adapter not connected")

        body: dict[str, str] = {
            "channel_id": message.chat_id,
            "message": message.text,
        }
        if message.reply_to:
            body["root_id"] = message.reply_to

        resp = await self._client.post(
            f"{self._url}{_POSTS}",
            json=body,
            headers=self._auth_headers(),
        )
        if resp.status_code not in (200, 201):
            logger.error(
                "mattermost_send_failed",
                channel_id=message.chat_id,
                status=resp.status_code,
                body=resp.text[:200],
            )

    async def healthcheck(self) -> bool:
        """Check if the Mattermost connection is healthy."""
        if not self._client:
            return False
        try:
            resp = await self._client.get(
                f"{self._url}{_ME}",
                headers=self._auth_headers(),
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Return authorization headers."""
        return {"Authorization": f"Bearer {self._token}"}

    async def _ws_loop(self) -> None:
        """Connect to the Mattermost WebSocket and dispatch events."""
        try:
            import websockets
        except ImportError:
            logger.warning(
                "mattermost_ws_unavailable",
                msg="websockets package not installed, falling back to polling",
            )
            await self._poll_loop()
            return

        ws_url = self._url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}{_WS}"

        try:
            async for ws in websockets.connect(ws_url):
                try:
                    # Authenticate over WebSocket
                    auth_msg = json.dumps({
                        "seq": self._ws_seq,
                        "action": "authentication_challenge",
                        "data": {"token": self._token},
                    })
                    self._ws_seq += 1
                    await ws.send(auth_msg)

                    async for raw_msg in ws:
                        data = json.loads(raw_msg)
                        self._handle_ws_event(data)
                except websockets.ConnectionClosed:
                    logger.warning("mattermost_ws_reconnecting")
                    continue
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("mattermost_ws_error")

    async def _poll_loop(self) -> None:
        """Fallback polling mode when websockets is not available."""
        try:
            last_time = int(datetime.now(UTC).timestamp() * 1000)
            while self._client:
                try:
                    resp = await self._client.get(
                        f"{self._url}/api/v4/posts?since={last_time}",
                        headers=self._auth_headers(),
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        posts = data.get("posts", {})
                        order = data.get("order", [])
                        for post_id in order:
                            post = posts.get(post_id, {})
                            self._process_post(post)
                        if order:
                            last_time = int(datetime.now(UTC).timestamp() * 1000)
                except Exception:
                    logger.exception("mattermost_poll_error")

                await asyncio.sleep(2)
        except asyncio.CancelledError:
            return

    def _handle_ws_event(self, data: dict) -> None:
        """Process a Mattermost WebSocket event."""
        event_type = data.get("event")
        if event_type != "posted":
            return

        event_data = data.get("data", {})
        post_str = event_data.get("post", "")
        if not post_str:
            return

        try:
            post = json.loads(post_str)
        except json.JSONDecodeError:
            return

        self._process_post(post)

    def _process_post(self, post: dict) -> None:
        """Convert a Mattermost post into an InboundMessage."""
        user_id = post.get("user_id", "")

        # Ignore own messages
        if user_id == self._user_id:
            return

        message = post.get("message", "")
        if not message:
            return

        create_at = post.get("create_at", 0)
        try:
            timestamp = datetime.fromtimestamp(create_at / 1000, tz=UTC)
        except (ValueError, OSError, OverflowError):
            timestamp = datetime.now(UTC)

        post_id = post.get("id", "")
        channel_id = post.get("channel_id", "")
        root_id = post.get("root_id", "") or None

        inbound = InboundMessage(
            id=post_id,
            platform="mattermost",
            sender_id=user_id,
            chat_id=channel_id,
            text=message,
            timestamp=timestamp,
            reply_to=root_id,
            raw=post,
        )
        self._message_queue.put_nowait(inbound)
