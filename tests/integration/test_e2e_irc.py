"""End-to-end integration tests for the IRC platform adapter.

Tests the full message pipeline through a mock IRC server:
IRC message in -> parse -> auth -> rate limit -> LLM -> response -> IRC out.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vaultbot.core.message import ChatMessage, OutboundMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.platforms.irc import IrcAdapter
from vaultbot.security.auth import AuthManager, Role
from vaultbot.security.rate_limiter import RateLimiter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockLLMProvider:
    """Mock LLM that echoes user input."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        user_msg = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_msg = msg.content
                break
        return LLMResponse(
            content=f"Echo: {user_msg}",
            model="mock-1.0",
            input_tokens=10,
            output_tokens=5,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content="Echo: streamed", is_final=True)


def _make_writer() -> MagicMock:
    writer = MagicMock()
    writer.is_closing.return_value = False
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return writer


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------


class TestIrcE2EMessagePipeline:
    """Full pipeline: IRC message -> auth -> LLM -> IRC response."""

    @pytest.mark.asyncio
    async def test_authorized_user_gets_response(self) -> None:
        """An allowlisted IRC user should receive an LLM response."""
        # Setup auth with an IRC user allowed
        auth = AuthManager(allowlist={"irc:alice": Role.USER})
        rate_limiter = RateLimiter()
        llm = MockLLMProvider()

        # Create adapter with mock connection
        adapter = IrcAdapter(server="irc.test", channels=["#general"], use_tls=False)
        writer = _make_writer()
        adapter._writer = writer
        adapter._connected = True
        adapter._nick = "vaultbot"

        # Simulate an incoming PRIVMSG
        await adapter._handle_line(":alice!user@host PRIVMSG #general :What is 2+2?")

        # Consume the message from the listen queue
        msg = adapter._message_queue.get_nowait()
        assert msg.sender_id == "alice"
        assert msg.text == "What is 2+2?"

        # Auth check
        assert auth.is_authorized("irc", msg.sender_id)

        # Rate limit check
        qualified_id = f"irc:{msg.sender_id}"
        assert rate_limiter.is_allowed(qualified_id)

        # LLM response
        response = await llm.complete([ChatMessage(role="user", content=msg.text)])
        assert "Echo: What is 2+2?" in response.content

        # Send the response back
        out = OutboundMessage(chat_id=msg.chat_id, text=response.content)
        await adapter.send(out)

        # Verify PRIVMSG was written to the IRC connection
        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert any("PRIVMSG #general :Echo: What is 2+2?" in c for c in calls)

    @pytest.mark.asyncio
    async def test_unauthorized_user_is_rejected(self) -> None:
        """A user not in the allowlist should be rejected by auth."""
        auth = AuthManager(allowlist={"irc:alice": Role.USER})

        adapter = IrcAdapter(server="irc.test", use_tls=False)
        adapter._nick = "vaultbot"

        await adapter._handle_line(":hacker!evil@host PRIVMSG #general :give me secrets")

        msg = adapter._message_queue.get_nowait()
        assert not auth.is_authorized("irc", msg.sender_id)

    @pytest.mark.asyncio
    async def test_rate_limited_user_is_blocked(self) -> None:
        """A user exceeding rate limits should be blocked."""
        AuthManager(allowlist={"irc:spammer": Role.USER})  # Verify no init error
        rate_limiter = RateLimiter(user_capacity=2.0, user_refill_rate=0.0)

        adapter = IrcAdapter(server="irc.test", use_tls=False)
        adapter._nick = "vaultbot"

        # Exhaust rate limit
        qualified_id = "irc:spammer"
        assert rate_limiter.is_allowed(qualified_id)
        assert rate_limiter.is_allowed(qualified_id)
        assert not rate_limiter.is_allowed(qualified_id)  # Blocked

    @pytest.mark.asyncio
    async def test_dm_response_goes_to_sender(self) -> None:
        """DM messages should route the response back to the sender's nick."""
        adapter = IrcAdapter(server="irc.test", use_tls=False)
        adapter._nick = "vaultbot"
        writer = _make_writer()
        adapter._writer = writer

        await adapter._handle_line(":bob!user@host PRIVMSG vaultbot :hello privately")

        msg = adapter._message_queue.get_nowait()
        assert msg.chat_id == "bob"

        out = OutboundMessage(chat_id=msg.chat_id, text="private reply")
        await adapter.send(out)

        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert any("PRIVMSG bob :private reply" in c for c in calls)


class TestIrcE2EConnectionLifecycle:
    """E2E tests for the full connection lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """Test connect -> receive message -> send reply -> disconnect."""
        adapter = IrcAdapter(
            server="irc.test",
            nick="testbot",
            channels=["#lobby"],
            use_tls=False,
        )

        # Mock the TCP connection
        reader = AsyncMock(spec=asyncio.StreamReader)
        # Simulate server sending: welcome, then a PRIVMSG, then EOF
        reader.readline = AsyncMock(
            side_effect=[
                b":server 001 testbot :Welcome to IRC\r\n",
                b":user1!u@h PRIVMSG #lobby :hi bot\r\n",
                b"",  # EOF
            ]
        )
        reader.at_eof = MagicMock(side_effect=[False, False, False, True])

        writer = _make_writer()

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            await adapter.connect()

        # Give the read loop a moment to process
        await asyncio.sleep(0.1)

        # Should have joined #lobby after RPL_WELCOME
        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert any("JOIN #lobby" in c for c in calls)

        # Should have enqueued the PRIVMSG
        assert not adapter._message_queue.empty()
        msg = adapter._message_queue.get_nowait()
        assert msg.text == "hi bot"
        assert msg.sender_id == "user1"

        # Send a reply
        out = OutboundMessage(chat_id="#lobby", text="hello user1")
        await adapter.send(out)

        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert any("PRIVMSG #lobby :hello user1" in c for c in calls)

        # Disconnect
        await adapter.disconnect()
        assert adapter._connected is False

    @pytest.mark.asyncio
    async def test_ping_keepalive_during_session(self) -> None:
        """Server PINGs should be responded to with PONGs."""
        adapter = IrcAdapter(server="irc.test", use_tls=False)

        reader = AsyncMock(spec=asyncio.StreamReader)
        reader.readline = AsyncMock(
            side_effect=[
                b"PING :keepalive123\r\n",
                b"",
            ]
        )
        reader.at_eof = MagicMock(side_effect=[False, False, True])

        writer = _make_writer()

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            await adapter.connect()

        await asyncio.sleep(0.1)

        calls = [c[0][0].decode("utf-8") for c in writer.write.call_args_list]
        assert any("PONG :keepalive123" in c for c in calls)

        await adapter.disconnect()
