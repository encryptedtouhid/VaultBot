"""Telegram messaging platform adapter using python-telegram-bot."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
)

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class TelegramAdapter:
    """Telegram bot adapter using polling mode."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._app: Application | None = None  # type: ignore[type-arg]
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()

    @property
    def platform_name(self) -> str:
        return "telegram"

    async def connect(self) -> None:
        """Initialize and start the Telegram bot."""
        self._app = (
            Application.builder()
            .token(self._token)
            .build()
        )

        # Register message handler that feeds into our queue
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )

        await self._app.initialize()
        await self._app.start()
        if self._app.updater:
            await self._app.updater.start_polling(drop_pending_updates=True)

        logger.info("telegram_connected")

    async def disconnect(self) -> None:
        """Stop the Telegram bot."""
        if self._app:
            if self._app.updater:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        logger.info("telegram_disconnected")

    async def _on_message(self, update: Update, _context: object) -> None:
        """Handle incoming Telegram messages by queueing them."""
        if not update.message or not update.message.text:
            return

        msg = update.message
        inbound = InboundMessage(
            id=str(msg.message_id),
            platform="telegram",
            sender_id=str(msg.from_user.id) if msg.from_user else "unknown",
            chat_id=str(msg.chat_id),
            text=msg.text,
            timestamp=msg.date.replace(tzinfo=UTC) if msg.date else datetime.now(UTC),
            reply_to=str(msg.reply_to_message.message_id) if msg.reply_to_message else None,
            raw=update,
        )
        await self._message_queue.put(inbound)

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from Telegram."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a message via Telegram."""
        if not self._app or not self._app.bot:
            raise RuntimeError("Telegram adapter not connected")

        try:
            chat_id = int(message.chat_id)
        except ValueError:
            logger.error("telegram_invalid_chat_id", chat_id=message.chat_id)
            return

        reply_to: int | None = None
        if message.reply_to:
            try:
                reply_to = int(message.reply_to)
            except ValueError:
                pass

        await self._app.bot.send_message(
            chat_id=chat_id,
            text=message.text,
            reply_to_message_id=reply_to,
        )

    async def healthcheck(self) -> bool:
        """Check if the Telegram bot is responsive."""
        if not self._app or not self._app.bot:
            return False
        try:
            me = await self._app.bot.get_me()
            return me is not None
        except Exception:
            return False
