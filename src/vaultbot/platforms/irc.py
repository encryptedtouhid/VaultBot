"""IRC messaging platform adapter.

Implements an async IRC client using the ``irc`` protocol directly over
``asyncio``.  Supports TLS connections, channel joins, private messages,
and nick management.  No third-party IRC library is required — the adapter
speaks the raw IRC protocol, keeping the dependency footprint minimal.
"""

from __future__ import annotations

import asyncio
import ssl
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# IRC line length limit (RFC 2812)
_MAX_LINE = 512


class IrcAdapter:
    """IRC bot adapter with TLS support.

    Parameters
    ----------
    server:
        IRC server hostname (e.g. ``irc.libera.chat``).
    port:
        IRC server port.  Defaults to ``6697`` (TLS).
    nick:
        Bot's nickname.
    channels:
        List of channels to join on connect (including ``#`` prefix).
    password:
        Optional server password (e.g. NickServ identification).
    use_tls:
        Whether to connect with TLS.  Defaults to ``True``.
    """

    def __init__(
        self,
        *,
        server: str,
        port: int = 6697,
        nick: str = "vaultbot",
        channels: list[str] | None = None,
        password: str = "",
        use_tls: bool = True,
    ) -> None:
        self._server = server
        self._port = port
        self._nick = nick
        self._channels = channels or []
        self._password = password
        self._use_tls = use_tls

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._connected = False
        self._read_task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # PlatformAdapter protocol
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "irc"

    async def connect(self) -> None:
        """Open a TCP (optionally TLS) connection and register with the server."""
        ssl_ctx: ssl.SSLContext | None = None
        if self._use_tls:
            ssl_ctx = ssl.create_default_context()

        self._reader, self._writer = await asyncio.open_connection(
            self._server, self._port, ssl=ssl_ctx,
        )

        # Send IRC registration sequence
        if self._password:
            await self._send_raw(f"PASS {self._password}")
        await self._send_raw(f"NICK {self._nick}")
        await self._send_raw(f"USER {self._nick} 0 * :VaultBot IRC Adapter")

        # Start background reader that processes server messages
        self._read_task = asyncio.create_task(self._read_loop())
        self._connected = True
        logger.info("irc_connected", server=self._server, port=self._port, nick=self._nick)

    async def disconnect(self) -> None:
        """Send QUIT and close the connection."""
        if self._writer and not self._writer.is_closing():
            try:
                await self._send_raw("QUIT :VaultBot signing off")
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
        logger.info("irc_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from IRC channels / private messages."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a PRIVMSG to the target channel or nick."""
        if not self._writer or self._writer.is_closing():
            raise RuntimeError("IRC adapter not connected")

        target = message.chat_id
        # Split long messages to respect the IRC line limit
        for line in message.text.splitlines():
            if line:
                await self._send_raw(f"PRIVMSG {target} :{line}")

    async def healthcheck(self) -> bool:
        """Return True if the TCP connection is alive."""
        return self._connected and self._writer is not None and not self._writer.is_closing()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _send_raw(self, data: str) -> None:
        """Write a single IRC command to the server."""
        if not self._writer or self._writer.is_closing():
            return
        # Truncate to IRC limit minus CRLF
        raw = data[:_MAX_LINE - 2] + "\r\n"
        self._writer.write(raw.encode("utf-8", errors="replace"))
        await self._writer.drain()

    async def _read_loop(self) -> None:
        """Continuously read lines from the server and dispatch them."""
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
            logger.exception("irc_read_error")
        finally:
            self._connected = False

    async def _handle_line(self, line: str) -> None:
        """Parse a raw IRC line and take appropriate action."""
        # Reply to PING to stay connected
        if line.startswith("PING"):
            token = line.split(" ", 1)[1] if " " in line else ""
            await self._send_raw(f"PONG {token}")
            return

        parts = line.split(" ")
        if len(parts) < 2:
            return

        prefix = parts[0]
        command = parts[1]

        # After successful registration, join configured channels
        if command == "001":  # RPL_WELCOME
            for channel in self._channels:
                await self._send_raw(f"JOIN {channel}")
            return

        if command == "PRIVMSG" and len(parts) >= 3:
            await self._handle_privmsg(prefix, parts)

    async def _handle_privmsg(self, prefix: str, parts: list[str]) -> None:
        """Parse and enqueue a PRIVMSG."""
        # prefix format: :nick!user@host
        sender_nick = prefix.lstrip(":").split("!")[0]

        # Ignore messages from self
        if sender_nick == self._nick:
            return

        target = parts[2]

        # Extract message text (everything after the first ':' in the trailing param)
        raw_text = " ".join(parts[3:])
        text = raw_text.lstrip(":")

        if not text:
            return

        # If target is the bot's nick, it's a DM — reply to sender
        chat_id = target if target.startswith("#") else sender_nick

        inbound = InboundMessage(
            id=f"{sender_nick}-{datetime.now(UTC).timestamp():.6f}",
            platform="irc",
            sender_id=sender_nick,
            chat_id=chat_id,
            text=text,
            timestamp=datetime.now(UTC),
            reply_to=None,
            raw={"prefix": prefix, "parts": parts},
        )
        await self._message_queue.put(inbound)
