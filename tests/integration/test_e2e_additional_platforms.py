"""E2E integration tests for LINE, Google Chat, Twitch, and Nostr adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.core.message import ChatMessage, OutboundMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.security.auth import AuthManager, Role


class MockLLMProvider:
    @property
    def provider_name(self) -> str:
        return "mock"

    async def complete(self, messages: list[ChatMessage], **kw: object) -> LLMResponse:
        user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return LLMResponse(content=f"Echo: {user_msg}", model="mock", input_tokens=10, output_tokens=5)

    async def stream(self, messages: list[ChatMessage], **kw: object) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content="Echo: streamed", is_final=True)


# ==========================================================================
# LINE E2E
# ==========================================================================


class TestLineE2E:
    @pytest.mark.asyncio
    async def test_webhook_to_reply(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        auth = AuthManager(allowlist={"line:user1": Role.USER})
        llm = MockLLMProvider()

        adapter = LineAdapter(channel_access_token="tok")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
        adapter._client = mock_client
        adapter._connected = True

        payload = {
            "events": [{
                "type": "message",
                "replyToken": "rt1",
                "source": {"userId": "user1"},
                "timestamp": 1700000000000,
                "message": {"id": "m1", "type": "text", "text": "What is LINE?"},
            }]
        }
        adapter.handle_webhook(payload)

        msg = adapter._message_queue.get_nowait()
        assert auth.is_authorized("line", msg.sender_id)

        response = await llm.complete([ChatMessage(role="user", content=msg.text)])
        await adapter.send(OutboundMessage(chat_id=msg.chat_id, text=response.content))

        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_unauthorized_line_user(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        auth = AuthManager(allowlist={"line:user1": Role.USER})

        adapter = LineAdapter(channel_access_token="tok")
        payload = {
            "events": [{
                "type": "message",
                "source": {"userId": "hacker"},
                "timestamp": 0,
                "message": {"id": "m2", "type": "text", "text": "hack"},
            }]
        }
        adapter.handle_webhook(payload)
        msg = adapter._message_queue.get_nowait()
        assert not auth.is_authorized("line", msg.sender_id)


# ==========================================================================
# Google Chat E2E
# ==========================================================================


class TestGoogleChatE2E:
    @pytest.mark.asyncio
    async def test_webhook_to_response(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        auth = AuthManager(allowlist={"googlechat:users/u1": Role.USER})
        llm = MockLLMProvider()

        adapter = GoogleChatAdapter(webhook_url="https://hooks.example.com")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
        adapter._client = mock_client
        adapter._connected = True

        payload = {
            "type": "MESSAGE",
            "message": {
                "name": "m1", "argumentText": "What is Go?",
                "sender": {"name": "users/u1"}, "createTime": "2024-01-01T00:00:00Z",
            },
            "space": {"name": "spaces/s1"},
        }
        adapter.handle_webhook(payload)

        msg = adapter._message_queue.get_nowait()
        assert auth.is_authorized("googlechat", msg.sender_id)

        response = await llm.complete([ChatMessage(role="user", content=msg.text)])
        await adapter.send(OutboundMessage(chat_id=msg.chat_id, text=response.content))
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_unauthorized_googlechat_user(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        auth = AuthManager(allowlist={"googlechat:users/u1": Role.USER})

        adapter = GoogleChatAdapter()
        payload = {
            "type": "MESSAGE",
            "message": {"name": "m2", "argumentText": "hack", "sender": {"name": "users/hacker"}, "createTime": ""},
            "space": {"name": "spaces/s1"},
        }
        adapter.handle_webhook(payload)
        msg = adapter._message_queue.get_nowait()
        assert not auth.is_authorized("googlechat", msg.sender_id)


# ==========================================================================
# Twitch E2E
# ==========================================================================


class TestTwitchE2E:
    @pytest.mark.asyncio
    async def test_message_to_response(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        auth = AuthManager(allowlist={"twitch:alice": Role.USER})
        llm = MockLLMProvider()

        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        adapter._writer = writer
        adapter._connected = True

        await adapter._handle_line(":alice!a@a.tmi.twitch.tv PRIVMSG #mychannel :What is Twitch?")

        msg = adapter._message_queue.get_nowait()
        assert auth.is_authorized("twitch", msg.sender_id)

        response = await llm.complete([ChatMessage(role="user", content=msg.text)])
        await adapter.send(OutboundMessage(chat_id=msg.chat_id, text=response.content))

        written = writer.write.call_args[0][0].decode("utf-8")
        assert "PRIVMSG #mychannel" in written

    @pytest.mark.asyncio
    async def test_unauthorized_twitch_user(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        auth = AuthManager(allowlist={"twitch:alice": Role.USER})

        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        await adapter._handle_line(":hacker!h@h.tmi.twitch.tv PRIVMSG #ch :gimme")

        msg = adapter._message_queue.get_nowait()
        assert not auth.is_authorized("twitch", msg.sender_id)


# ==========================================================================
# Nostr E2E
# ==========================================================================


class TestNostrE2E:
    @pytest.mark.asyncio
    async def test_event_to_response(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        auth = AuthManager(allowlist={"nostr:sender_pub": Role.USER})
        llm = MockLLMProvider()

        adapter = NostrAdapter(public_key_hex="mypub")
        adapter._connected = True

        event = {
            "id": "e1", "pubkey": "sender_pub", "created_at": 1700000000,
            "kind": 1, "tags": [], "content": "What is Nostr?",
        }
        adapter._process_event(event)

        msg = adapter._message_queue.get_nowait()
        assert auth.is_authorized("nostr", msg.sender_id)

        response = await llm.complete([ChatMessage(role="user", content=msg.text)])
        assert "Echo: What is Nostr?" in response.content

    @pytest.mark.asyncio
    async def test_unauthorized_nostr_user(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        auth = AuthManager(allowlist={"nostr:trusted": Role.USER})

        adapter = NostrAdapter(public_key_hex="mypub")
        event = {"id": "e2", "pubkey": "untrusted", "created_at": 0, "kind": 1, "tags": [], "content": "hi"}
        adapter._process_event(event)

        msg = adapter._message_queue.get_nowait()
        assert not auth.is_authorized("nostr", msg.sender_id)

    @pytest.mark.asyncio
    async def test_multiple_events_processed(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="mypub")

        for i in range(3):
            event = {"id": f"e{i}", "pubkey": f"pub{i}", "created_at": 0, "kind": 1, "tags": [], "content": f"msg{i}"}
            adapter._process_event(event)

        messages = []
        while not adapter._message_queue.empty():
            messages.append(adapter._message_queue.get_nowait())
        assert len(messages) == 3
