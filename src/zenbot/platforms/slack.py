"""Slack messaging platform adapter.

Uses Slack's Bolt for Python (async) framework with Socket Mode
for receiving events without exposing a public endpoint. Also supports
webhook mode for production deployments.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

try:
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    from slack_bolt.async_app import AsyncApp
    from slack_sdk.web.async_client import AsyncWebClient

    _SLACK_AVAILABLE = True
except ImportError:
    _SLACK_AVAILABLE = False

from zenbot.core.message import InboundMessage, OutboundMessage
from zenbot.utils.logging import get_logger

logger = get_logger(__name__)


class SlackAdapter:
    """Slack bot adapter using Bolt for Python (async).

    Supports Socket Mode (no public URL needed) and Events API.
    Requires:
        - Bot token (xoxb-...)
        - App-level token (xapp-...) for Socket Mode
    """

    def __init__(
        self,
        *,
        bot_token: str,
        app_token: str = "",
        use_socket_mode: bool = True,
    ) -> None:
        if not _SLACK_AVAILABLE:
            raise ImportError(
                "Slack support requires 'slack-bolt' and 'slack-sdk'. "
                "Install with: pip install slack-bolt slack-sdk"
            )
        self._bot_token = bot_token
        self._app_token = app_token
        self._use_socket_mode = use_socket_mode
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._app = AsyncApp(token=bot_token)
        self._handler: AsyncSocketModeHandler | None = None
        self._setup_handlers()

    @property
    def platform_name(self) -> str:
        return "slack"

    def _setup_handlers(self) -> None:
        """Register Slack event handlers."""

        @self._app.event("message")
        async def handle_message(event: dict, say: object) -> None:  # type: ignore[type-arg]
            # Ignore bot messages and message_changed subtypes
            if event.get("bot_id") or event.get("subtype"):
                return

            text = event.get("text", "")
            if not text:
                return

            ts = event.get("ts", "0")
            try:
                timestamp = datetime.fromtimestamp(float(ts), tz=UTC)
            except (ValueError, OSError):
                timestamp = datetime.now(UTC)

            inbound = InboundMessage(
                id=ts,
                platform="slack",
                sender_id=event.get("user", "unknown"),
                chat_id=event.get("channel", "unknown"),
                text=text,
                timestamp=timestamp,
                reply_to=event.get("thread_ts"),
                raw=event,
            )
            await self._message_queue.put(inbound)

    async def connect(self) -> None:
        """Start the Slack bot."""
        if self._use_socket_mode and self._app_token:
            self._handler = AsyncSocketModeHandler(self._app, self._app_token)
            await self._handler.start_async()
            logger.info("slack_connected", mode="socket_mode")
        else:
            logger.info("slack_connected", mode="events_api")

    async def disconnect(self) -> None:
        """Stop the Slack bot."""
        if self._handler:
            await self._handler.close_async()
        logger.info("slack_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from Slack."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a message to a Slack channel."""
        client = AsyncWebClient(token=self._bot_token)
        kwargs: dict[str, object] = {
            "channel": message.chat_id,
            "text": message.text,
        }
        if message.reply_to:
            kwargs["thread_ts"] = message.reply_to

        await client.chat_postMessage(**kwargs)  # type: ignore[arg-type]

    async def healthcheck(self) -> bool:
        """Check if the Slack bot is connected."""
        try:
            client = AsyncWebClient(token=self._bot_token)
            result = await client.auth_test()
            return result.get("ok", False)  # type: ignore[union-attr]
        except Exception:
            return False
