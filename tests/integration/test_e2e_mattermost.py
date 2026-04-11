"""End-to-end integration tests for the Mattermost platform adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.core.message import ChatMessage, OutboundMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.platforms.mattermost import MattermostAdapter
from vaultbot.security.auth import AuthManager, Role
from vaultbot.security.rate_limiter import RateLimiter


class MockLLMProvider:
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
        return LLMResponse(content=f"Echo: {user_msg}", model="mock-1.0", input_tokens=10, output_tokens=5)

    async def stream(self, messages: list[ChatMessage], **kw: object) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content="Echo: streamed", is_final=True)


def _make_mock_client() -> AsyncMock:
    resp = MagicMock()
    resp.status_code = 201
    resp.text = ""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=resp)
    mock_client.get = AsyncMock(return_value=resp)
    mock_client.aclose = AsyncMock()
    return mock_client


class TestMattermostE2EMessagePipeline:
    """Full pipeline: Mattermost post -> auth -> LLM -> Mattermost response."""

    @pytest.mark.asyncio
    async def test_authorized_user_gets_response(self) -> None:
        auth = AuthManager(allowlist={"mattermost:alice_id": Role.USER})
        llm = MockLLMProvider()

        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_id"
        adapter._client = _make_mock_client()
        adapter._connected = True

        post = {
            "id": "p1", "user_id": "alice_id", "channel_id": "ch1",
            "message": "What is Rust?", "create_at": 1700000000000,
        }
        adapter._process_post(post)

        msg = adapter._message_queue.get_nowait()
        assert auth.is_authorized("mattermost", msg.sender_id)

        response = await llm.complete([ChatMessage(role="user", content=msg.text)])
        out = OutboundMessage(chat_id=msg.chat_id, text=response.content)
        await adapter.send(out)

        adapter._client.post.assert_called_once()
        call_kwargs = adapter._client.post.call_args
        assert call_kwargs[1]["json"]["message"] == "Echo: What is Rust?"

    @pytest.mark.asyncio
    async def test_unauthorized_user_rejected(self) -> None:
        auth = AuthManager(allowlist={"mattermost:alice_id": Role.USER})
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_id"

        post = {"id": "p2", "user_id": "hacker_id", "channel_id": "ch1", "message": "gimme", "create_at": 0}
        adapter._process_post(post)

        msg = adapter._message_queue.get_nowait()
        assert not auth.is_authorized("mattermost", msg.sender_id)

    @pytest.mark.asyncio
    async def test_rate_limited_user_blocked(self) -> None:
        rate_limiter = RateLimiter(user_capacity=1.0, user_refill_rate=0.0)
        qid = "mattermost:spammer"
        assert rate_limiter.is_allowed(qid)
        assert not rate_limiter.is_allowed(qid)

    @pytest.mark.asyncio
    async def test_threaded_reply_preserved(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_id"
        adapter._client = _make_mock_client()

        post = {
            "id": "p3", "user_id": "bob_id", "channel_id": "ch1",
            "message": "thread reply", "create_at": 1700000000000, "root_id": "p1",
        }
        adapter._process_post(post)

        msg = adapter._message_queue.get_nowait()
        assert msg.reply_to == "p1"

        out = OutboundMessage(chat_id=msg.chat_id, text="response", reply_to=msg.reply_to)
        await adapter.send(out)

        call_kwargs = adapter._client.post.call_args
        assert call_kwargs[1]["json"]["root_id"] == "p1"


class TestMattermostE2EWebSocketEvents:
    """E2E tests for WebSocket event flow."""

    @pytest.mark.asyncio
    async def test_ws_event_to_response(self) -> None:
        """Simulate full WS event -> process -> LLM -> send flow."""
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_id"
        adapter._client = _make_mock_client()
        llm = MockLLMProvider()

        post = {"id": "wp1", "user_id": "carol_id", "channel_id": "ch2", "message": "via ws", "create_at": 1700000000000}
        ws_event = {"event": "posted", "data": {"post": json.dumps(post)}}
        adapter._handle_ws_event(ws_event)

        msg = adapter._message_queue.get_nowait()
        assert msg.text == "via ws"

        response = await llm.complete([ChatMessage(role="user", content=msg.text)])
        out = OutboundMessage(chat_id=msg.chat_id, text=response.content)
        await adapter.send(out)

        adapter._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_ws_events_processed(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_id"

        for i in range(3):
            post = {"id": f"wp{i}", "user_id": f"user{i}", "channel_id": "ch1", "message": f"msg{i}", "create_at": 1700000000000}
            adapter._handle_ws_event({"event": "posted", "data": {"post": json.dumps(post)}})

        messages = []
        while not adapter._message_queue.empty():
            messages.append(adapter._message_queue.get_nowait())

        assert len(messages) == 3
        assert [m.text for m in messages] == ["msg0", "msg1", "msg2"]
