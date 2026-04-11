"""Discord messaging platform adapter using nextcord."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC

import nextcord
from nextcord.ext import commands

from zenbot.core.message import InboundMessage, OutboundMessage
from zenbot.utils.logging import get_logger

logger = get_logger(__name__)


class DiscordAdapter:
    """Discord bot adapter using nextcord."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        intents = nextcord.Intents.default()
        intents.message_content = True
        self._bot = commands.Bot(intents=intents)
        self._setup_handlers()

    @property
    def platform_name(self) -> str:
        return "discord"

    def _setup_handlers(self) -> None:
        """Register event handlers on the bot."""

        @self._bot.event
        async def on_ready() -> None:
            logger.info("discord_ready", user=str(self._bot.user))

        @self._bot.event
        async def on_message(message: nextcord.Message) -> None:
            # Ignore messages from the bot itself
            if message.author == self._bot.user:
                return
            # Ignore bot commands (handled separately if needed)
            if message.content.startswith("!"):
                return

            inbound = InboundMessage(
                id=str(message.id),
                platform="discord",
                sender_id=str(message.author.id),
                chat_id=str(message.channel.id),
                text=message.content,
                timestamp=message.created_at.replace(tzinfo=UTC)
                if message.created_at.tzinfo is None
                else message.created_at,
                reply_to=str(message.reference.message_id)
                if message.reference and message.reference.message_id
                else None,
                raw=message,
            )
            await self._message_queue.put(inbound)

    async def connect(self) -> None:
        """Start the Discord bot in the background."""
        asyncio.create_task(self._bot.start(self._token))
        # Wait for the bot to be ready
        await self._bot.wait_until_ready()
        logger.info("discord_connected")

    async def disconnect(self) -> None:
        """Close the Discord bot connection."""
        await self._bot.close()
        logger.info("discord_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from Discord."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a message to a Discord channel."""
        try:
            channel_id = int(message.chat_id)
        except ValueError:
            logger.error("discord_invalid_channel_id", chat_id=message.chat_id)
            return

        channel = self._bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self._bot.fetch_channel(channel_id)
            except nextcord.NotFound:
                logger.error("discord_channel_not_found", channel_id=message.chat_id)
                return

        if not isinstance(channel, nextcord.abc.Messageable):
            logger.error("discord_not_messageable", channel_id=message.chat_id)
            return

        kwargs: dict[str, object] = {"content": message.text}
        if message.reply_to:
            try:
                ref_msg = await channel.fetch_message(int(message.reply_to))
                kwargs["reference"] = ref_msg
            except (nextcord.NotFound, ValueError):
                pass

        await channel.send(**kwargs)  # type: ignore[arg-type]

    async def healthcheck(self) -> bool:
        """Check if the Discord bot is connected."""
        return self._bot.is_ready()
