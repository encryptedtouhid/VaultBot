"""Unit tests for the IRC platform adapter."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vaultbot.core.message import OutboundMessage
from vaultbot.platforms.irc import IrcAdapter

# ---------------------------------------------------------------------------
# Construction / properties
# ---------------------------------------------------------------------------


class TestIrcAdapterInit:
    """Tests for IrcAdapter construction and properties."""

    def test_platform_name(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        assert adapter.platform_name == "irc"

    def test_default_port_is_tls(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        assert adapter._port == 6697

    def test_custom_nick(self) -> None:
        adapter = IrcAdapter(server="irc.example.com", nick="mybot")
        assert adapter._nick == "mybot"

    def test_channels_stored(self) -> None:
        adapter = IrcAdapter(server="irc.example.com", channels=["#foo", "#bar"])
        assert adapter._channels == ["#foo", "#bar"]

    def test_tls_enabled_by_default(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        assert adapter._use_tls is True

    def test_tls_can_be_disabled(self) -> None:
        adapter = IrcAdapter(server="irc.example.com", use_tls=False)
        assert adapter._use_tls is False

    def test_initial_state_not_connected(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        assert adapter._connected is False


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------


class TestIrcHealthcheck:
    """Tests for the healthcheck method."""

    @pytest.mark.asyncio
    async def test_unhealthy_when_disconnected(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        assert await adapter.healthcheck() is False

    @pytest.mark.asyncio
    async def test_healthy_when_connected(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        adapter._connected = True
        writer = MagicMock()
        writer.is_closing.return_value = False
        adapter._writer = writer
        assert await adapter.healthcheck() is True

    @pytest.mark.asyncio
    async def test_unhealthy_when_writer_closing(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        adapter._connected = True
        writer = MagicMock()
        writer.is_closing.return_value = True
        adapter._writer = writer
        assert await adapter.healthcheck() is False


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------


class TestIrcSend:
    """Tests for sending messages."""

    @pytest.mark.asyncio
    async def test_send_raises_when_not_connected(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        msg = OutboundMessage(chat_id="#test", text="hello")
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.send(msg)

    @pytest.mark.asyncio
    async def test_send_writes_privmsg(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        adapter._writer = writer

        msg = OutboundMessage(chat_id="#general", text="hello world")
        await adapter.send(msg)

        writer.write.assert_called_once()
        written = writer.write.call_args[0][0].decode("utf-8")
        assert "PRIVMSG #general :hello world\r\n" in written

    @pytest.mark.asyncio
    async def test_send_multiline_splits(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        adapter._writer = writer

        msg = OutboundMessage(chat_id="#ch", text="line1\nline2")
        await adapter.send(msg)

        assert writer.write.call_count == 2


# ---------------------------------------------------------------------------
# Line handling (PING / PONG, PRIVMSG, RPL_WELCOME)
# ---------------------------------------------------------------------------


class TestIrcLineHandling:
    """Tests for internal IRC line parsing."""

    @pytest.mark.asyncio
    async def test_ping_pong(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        adapter._writer = writer

        await adapter._handle_line("PING :server123")

        written = writer.write.call_args[0][0].decode("utf-8")
        assert written.startswith("PONG :server123")

    @pytest.mark.asyncio
    async def test_welcome_joins_channels(self) -> None:
        adapter = IrcAdapter(server="irc.example.com", channels=["#dev", "#ops"])
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        adapter._writer = writer

        await adapter._handle_line(":server 001 vaultbot :Welcome")

        assert writer.write.call_count == 2
        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert any("JOIN #dev" in c for c in calls)
        assert any("JOIN #ops" in c for c in calls)

    @pytest.mark.asyncio
    async def test_privmsg_channel_enqueued(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        adapter._nick = "vaultbot"

        await adapter._handle_line(":alice!user@host PRIVMSG #general :hello bot")

        msg = adapter._message_queue.get_nowait()
        assert msg.platform == "irc"
        assert msg.sender_id == "alice"
        assert msg.chat_id == "#general"
        assert msg.text == "hello bot"

    @pytest.mark.asyncio
    async def test_privmsg_dm_uses_sender_as_chat_id(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        adapter._nick = "vaultbot"

        await adapter._handle_line(":bob!user@host PRIVMSG vaultbot :secret msg")

        msg = adapter._message_queue.get_nowait()
        assert msg.chat_id == "bob"
        assert msg.text == "secret msg"

    @pytest.mark.asyncio
    async def test_self_messages_ignored(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        adapter._nick = "vaultbot"

        await adapter._handle_line(":vaultbot!user@host PRIVMSG #general :my own msg")

        assert adapter._message_queue.empty()

    @pytest.mark.asyncio
    async def test_empty_text_ignored(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        adapter._nick = "vaultbot"

        await adapter._handle_line(":alice!user@host PRIVMSG #general :")

        assert adapter._message_queue.empty()

    @pytest.mark.asyncio
    async def test_short_line_ignored(self) -> None:
        """Lines with fewer than 2 parts should not crash."""
        adapter = IrcAdapter(server="irc.example.com")
        await adapter._handle_line("ONLYONE")
        # No error, no message enqueued
        assert adapter._message_queue.empty()


# ---------------------------------------------------------------------------
# Connect / Disconnect
# ---------------------------------------------------------------------------


class TestIrcConnectDisconnect:
    """Tests for connect and disconnect lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_sends_registration(self) -> None:
        adapter = IrcAdapter(
            server="irc.example.com",
            nick="testbot",
            password="secret",
            use_tls=False,
        )

        reader = AsyncMock(spec=asyncio.StreamReader)
        reader.at_eof.return_value = True  # Stop read loop immediately
        reader.readline = AsyncMock(return_value=b"")

        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            await adapter.connect()

        # Should have sent PASS, NICK, USER
        assert writer.write.call_count >= 3
        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert any("PASS secret" in c for c in calls)
        assert any("NICK testbot" in c for c in calls)
        assert any("USER testbot" in c for c in calls)
        assert adapter._connected is True

        # Cleanup
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_connect_without_password_skips_pass(self) -> None:
        adapter = IrcAdapter(server="irc.example.com", nick="bot", use_tls=False)

        reader = AsyncMock(spec=asyncio.StreamReader)
        reader.at_eof.return_value = True
        reader.readline = AsyncMock(return_value=b"")

        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            await adapter.connect()

        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert not any("PASS" in c for c in calls)
        assert adapter._connected is True

        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_sends_quit(self) -> None:
        adapter = IrcAdapter(server="irc.example.com", use_tls=False)

        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        adapter._writer = writer
        adapter._connected = True

        await adapter.disconnect()

        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert any("QUIT" in c for c in calls)
        assert adapter._connected is False

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self) -> None:
        """Calling disconnect when already disconnected should not crash."""
        adapter = IrcAdapter(server="irc.example.com")
        await adapter.disconnect()
        assert adapter._connected is False


# ---------------------------------------------------------------------------
# Listen iterator
# ---------------------------------------------------------------------------


class TestIrcListen:
    """Tests for the listen async iterator."""

    @pytest.mark.asyncio
    async def test_listen_yields_enqueued_messages(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        adapter._nick = "vaultbot"

        # Enqueue a PRIVMSG via internal handler
        await adapter._handle_line(":carol!u@h PRIVMSG #test :hi there")

        messages: list = []
        async for msg in adapter.listen():
            messages.append(msg)
            break  # Only consume one

        assert len(messages) == 1
        assert messages[0].text == "hi there"
        assert messages[0].sender_id == "carol"


# ---------------------------------------------------------------------------
# _send_raw edge cases
# ---------------------------------------------------------------------------


class TestSendRaw:
    """Tests for the low-level _send_raw helper."""

    @pytest.mark.asyncio
    async def test_send_raw_noop_when_no_writer(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        # Should not raise
        await adapter._send_raw("NICK test")

    @pytest.mark.asyncio
    async def test_send_raw_truncates_long_lines(self) -> None:
        adapter = IrcAdapter(server="irc.example.com")
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        adapter._writer = writer

        long_msg = "A" * 600
        await adapter._send_raw(long_msg)

        written = writer.write.call_args[0][0]
        # 510 chars + \r\n = 512
        assert len(written) <= 512
