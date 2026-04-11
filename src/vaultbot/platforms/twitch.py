"""Twitch messaging platform adapter.

Implements an async Twitch IRC bot using the Twitch IRC gateway.
Twitch chat uses IRC protocol with OAuth authentication over TLS.
"""

from __future__ import annotations

import asyncio
import ssl
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_TWITCH_IRC_HOST = "irc.chat.twitch.tv"
_TWITCH_IRC_PORT = 6697


class TwitchAdapter:
    """Twitch chat bot adapter via IRC gateway.

    Parameters
    ----------
    oauth_token:
        OAuth token (with ``oauth:`` prefix or without).
    nick:
        Bot's Twitch username (lowercase).
    channels:
        List of channels to join (without ``#`` prefix).
    """

    def __init__(
        self,
        *,
        oauth_token: str,
        nick: str,
        channels: list[str] | None = None,
    ) -> None:
        token = oauth_token if oauth_token.startswith("oauth:") else f"oauth:{oauth_token}"
        self._token = token
        self._nick = nick.lower()
        self._channels = [c.lower().lstrip("#") for c in (channels or [])]
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._connected = False
        self._read_task: asyncio.Task[None] | None = None

    @property
    def platform_name(self) -> str:
        return "twitch"

    async def connect(self) -> None:
        ssl_ctx = ssl.create_default_context()
        self._reader, self._writer = await asyncio.open_connection(
            _TWITCH_IRC_HOST, _TWITCH_IRC_PORT, ssl=ssl_ctx,
        )

        await self._send_raw(f"PASS {self._token}")
        await self._send_raw(f"NICK {self._nick}")
        await self._send_raw("CAP REQ :twitch.tv/tags twitch.tv/commands")

        for channel in self._channels:
            await self._send_raw(f"JOIN #{channel}")

        self._read_task = asyncio.create_task(self._read_loop())
        self._connected = True
        logger.info("twitch_connected", nick=self._nick, channels=self._channels)

    async def disconnect(self) -> None:
        if self._writer and not self._writer.is_closing():
            try:
                await self._send_raw("QUIT")
            except Exception:
                pass
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        self._connected = False
        self._reader = None
        self._writer = None
        logger.info("twitch_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        if not self._writer or self._writer.is_closing():
            raise RuntimeError("Twitch adapter not connected")

        channel = message.chat_id if message.chat_id.startswith("#") else f"#{message.chat_id}"
        for line in message.text.splitlines():
            if line:
                await self._send_raw(f"PRIVMSG {channel} :{line}")

    async def healthcheck(self) -> bool:
        return self._connected and self._writer is not None and not self._writer.is_closing()

    async def _send_raw(self, data: str) -> None:
        if not self._writer or self._writer.is_closing():
            return
        raw = data[:510] + "\r\n"
        self._writer.write(raw.encode("utf-8", errors="replace"))
        await self._writer.drain()

    async def _read_loop(self) -> None:
        try:
            while self._reader and not self._reader.at_eof():
                raw_line = await self._reader.readline()
                if not raw_line:
                    break
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line:
                    await self._handle_line(line)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("twitch_read_error")
        finally:
            self._connected = False

    async def _handle_line(self, line: str) -> None:
        if line.startswith("PING"):
            token = line.split(" ", 1)[1] if " " in line else ":tmi.twitch.tv"
            await self._send_raw(f"PONG {token}")
            return

        # Parse Twitch IRC message: [@tags] :nick!user@host PRIVMSG #channel :text
        # Strip optional tags prefix
        raw = line
        if raw.startswith("@"):
            _, raw = raw.split(" ", 1)

        parts = raw.split(" ")
        if len(parts) < 3:
            return

        prefix = parts[0]
        command = parts[1]

        if command == "PRIVMSG" and len(parts) >= 3:
            sender_nick = prefix.lstrip(":").split("!")[0]
            if sender_nick == self._nick:
                return

            channel = parts[2]
            text = " ".join(parts[3:]).lstrip(":")
            if not text:
                return

            inbound = InboundMessage(
                id=f"{sender_nick}-{datetime.now(UTC).timestamp():.6f}",
                platform="twitch",
                sender_id=sender_nick,
                chat_id=channel,
                text=text,
                timestamp=datetime.now(UTC),
                raw={"line": line},
            )
            self._message_queue.put_nowait(inbound)
