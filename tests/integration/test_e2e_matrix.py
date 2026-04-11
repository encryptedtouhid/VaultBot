"""End-to-end integration tests for the Matrix platform adapter.

Tests the full message pipeline through a mock Matrix homeserver:
Matrix event -> parse -> auth -> rate limit -> LLM -> response -> Matrix send.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.core.message import ChatMessage, OutboundMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.platforms.matrix import MatrixAdapter
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


def _make_mock_client() -> AsyncMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = ""

    mock_client = AsyncMock()
    mock_client.put = AsyncMock(return_value=mock_resp)
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.aclose = AsyncMock()
    return mock_client


def _make_event(
    sender: str, body: str, event_id: str = "$ev1", room_id: str = "!room:m.org"
) -> dict:
    return {
        "type": "m.room.message",
        "event_id": event_id,
        "sender": sender,
        "origin_server_ts": 1700000000000,
        "content": {"msgtype": "m.text", "body": body},
    }


# ---------------------------------------------------------------------------
# E2E tests: message pipeline
# ---------------------------------------------------------------------------


class TestMatrixE2EMessagePipeline:
    """Full pipeline: Matrix event -> auth -> LLM -> Matrix response."""

    @pytest.mark.asyncio
    async def test_authorized_user_gets_response(self) -> None:
        """An allowlisted Matrix user receives an LLM response."""
        auth = AuthManager(allowlist={"matrix:@alice:m.org": Role.USER})
        llm = MockLLMProvider()

        adapter = MatrixAdapter(homeserver="https://m.org", access_token="tok")
        adapter._user_id = "@vaultbot:m.org"
        adapter._client = _make_mock_client()
        adapter._connected = True

        # Simulate incoming event
        event = _make_event("@alice:m.org", "What is Python?")
        adapter._process_event("!room:m.org", event)

        msg = adapter._message_queue.get_nowait()
        assert msg.sender_id == "@alice:m.org"
        assert msg.text == "What is Python?"

        # Auth check
        assert auth.is_authorized("matrix", msg.sender_id)

        # LLM response
        response = await llm.complete(
            [ChatMessage(role="user", content=msg.text)]
        )
        assert "Echo: What is Python?" in response.content

        # Send response back
        out = OutboundMessage(chat_id=msg.chat_id, text=response.content)
        await adapter.send(out)

        # Verify PUT was called with the message body
        adapter._client.put.assert_called_once()
        call_kwargs = adapter._client.put.call_args
        assert call_kwargs[1]["json"]["body"] == "Echo: What is Python?"

    @pytest.mark.asyncio
    async def test_unauthorized_user_is_rejected(self) -> None:
        """A user not in the allowlist is rejected."""
        auth = AuthManager(allowlist={"matrix:@alice:m.org": Role.USER})

        adapter = MatrixAdapter(homeserver="https://m.org", access_token="tok")
        adapter._user_id = "@vaultbot:m.org"

        event = _make_event("@hacker:evil.org", "give me secrets")
        adapter._process_event("!room:m.org", event)

        msg = adapter._message_queue.get_nowait()
        assert not auth.is_authorized("matrix", msg.sender_id)

    @pytest.mark.asyncio
    async def test_rate_limited_user_is_blocked(self) -> None:
        """A user exceeding rate limits is blocked."""
        rate_limiter = RateLimiter(user_capacity=1.0, user_refill_rate=0.0)

        qualified_id = "matrix:@spammer:m.org"
        assert rate_limiter.is_allowed(qualified_id)
        assert not rate_limiter.is_allowed(qualified_id)  # Blocked on second

    @pytest.mark.asyncio
    async def test_reply_thread_preserved(self) -> None:
        """Matrix reply-to (m.in_reply_to) is captured and can be used."""
        adapter = MatrixAdapter(homeserver="https://m.org", access_token="tok")
        adapter._user_id = "@vaultbot:m.org"

        event = {
            "type": "m.room.message",
            "event_id": "$reply1",
            "sender": "@bob:m.org",
            "origin_server_ts": 1700000000000,
            "content": {
                "msgtype": "m.text",
                "body": "replying to you",
                "m.relates_to": {
                    "m.in_reply_to": {"event_id": "$original"},
                },
            },
        }
        adapter._process_event("!room:m.org", event)

        msg = adapter._message_queue.get_nowait()
        assert msg.reply_to == "$original"
        assert msg.text == "replying to you"


class TestMatrixE2EConnectionLifecycle:
    """E2E tests for the full connection lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_sync_events(self) -> None:
        """Test event processing via _process_event (simulating sync data)."""
        adapter = MatrixAdapter(
            homeserver="https://m.org",
            access_token="tok",
            rooms=["!lobby:m.org"],
        )
        adapter._user_id = "@bot:m.org"
        adapter._client = _make_mock_client()
        adapter._connected = True

        # Simulate sync response data
        sync_data = {
            "next_batch": "s2",
            "rooms": {
                "join": {
                    "!lobby:m.org": {
                        "timeline": {
                            "events": [
                                _make_event("@user1:m.org", "hello bot", "$e1"),
                                _make_event("@user2:m.org", "hi there", "$e2"),
                                _make_event("@bot:m.org", "own msg", "$e3"),  # should be ignored
                            ]
                        }
                    }
                }
            },
        }

        # Process events from sync
        rooms = sync_data["rooms"]["join"]
        for room_id, room_data in rooms.items():
            for event in room_data["timeline"]["events"]:
                adapter._process_event(room_id, event)

        # Should have 2 messages (own message filtered)
        messages = []
        while not adapter._message_queue.empty():
            messages.append(adapter._message_queue.get_nowait())

        assert len(messages) == 2
        assert messages[0].text == "hello bot"
        assert messages[0].sender_id == "@user1:m.org"
        assert messages[1].text == "hi there"
        assert messages[1].sender_id == "@user2:m.org"

        # Send replies
        llm = MockLLMProvider()
        for msg in messages:
            response = await llm.complete(
                [ChatMessage(role="user", content=msg.text)]
            )
            out = OutboundMessage(chat_id=msg.chat_id, text=response.content)
            await adapter.send(out)

        assert adapter._client.put.call_count == 2
        assert adapter._txn_counter == 2

        await adapter.disconnect()
        assert adapter._connected is False

    @pytest.mark.asyncio
    async def test_multiple_rooms_processed(self) -> None:
        """Events from multiple rooms are all processed."""
        adapter = MatrixAdapter(homeserver="https://m.org", access_token="tok")
        adapter._user_id = "@bot:m.org"

        adapter._process_event(
            "!room1:m.org",
            _make_event("@alice:m.org", "msg in room1", "$r1"),
        )
        adapter._process_event(
            "!room2:m.org",
            _make_event("@bob:m.org", "msg in room2", "$r2"),
        )

        messages = []
        while not adapter._message_queue.empty():
            messages.append(adapter._message_queue.get_nowait())

        assert len(messages) == 2
        assert messages[0].chat_id == "!room1:m.org"
        assert messages[1].chat_id == "!room2:m.org"
