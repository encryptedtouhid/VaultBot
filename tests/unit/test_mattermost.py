"""Unit tests for the Mattermost platform adapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.core.message import OutboundMessage
from vaultbot.platforms.mattermost import MattermostAdapter

# ---------------------------------------------------------------------------
# Construction / properties
# ---------------------------------------------------------------------------


class TestMattermostAdapterInit:
    """Tests for MattermostAdapter construction and properties."""

    def test_platform_name(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        assert adapter.platform_name == "mattermost"

    def test_url_trailing_slash_stripped(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com/", token="tok")
        assert adapter._url == "https://chat.example.com"

    def test_initial_state_not_connected(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        assert adapter._connected is False

    def test_user_id_empty_initially(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        assert adapter._user_id == ""


# ---------------------------------------------------------------------------
# Auth headers
# ---------------------------------------------------------------------------


class TestMattermostHelpers:
    """Tests for internal helper methods."""

    def test_auth_headers(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="my_token")
        headers = adapter._auth_headers()
        assert headers["Authorization"] == "Bearer my_token"


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------


class TestMattermostHealthcheck:
    """Tests for the healthcheck method."""

    @pytest.mark.asyncio
    async def test_unhealthy_when_disconnected(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        assert await adapter.healthcheck() is False

    @pytest.mark.asyncio
    async def test_healthy_when_me_succeeds(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        assert await adapter.healthcheck() is True

    @pytest.mark.asyncio
    async def test_unhealthy_when_me_fails(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 401

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        assert await adapter.healthcheck() is False

    @pytest.mark.asyncio
    async def test_unhealthy_on_exception(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("timeout"))
        adapter._client = mock_client

        assert await adapter.healthcheck() is False


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------


class TestMattermostSend:
    """Tests for sending messages."""

    @pytest.mark.asyncio
    async def test_send_raises_when_not_connected(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        msg = OutboundMessage(chat_id="channel123", text="hello")
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.send(msg)

    @pytest.mark.asyncio
    async def test_send_posts_message(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 201

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        msg = OutboundMessage(chat_id="ch123", text="hello world")
        await adapter.send(msg)

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[1]["json"]["channel_id"] == "ch123"
        assert call_kwargs[1]["json"]["message"] == "hello world"

    @pytest.mark.asyncio
    async def test_send_with_reply_to_includes_root_id(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 201

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        msg = OutboundMessage(chat_id="ch123", text="reply", reply_to="post456")
        await adapter.send(msg)

        call_kwargs = mock_client.post.call_args
        assert call_kwargs[1]["json"]["root_id"] == "post456"

    @pytest.mark.asyncio
    async def test_send_logs_error_on_failure(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        msg = OutboundMessage(chat_id="ch123", text="test")
        await adapter.send(msg)  # Should not raise


# ---------------------------------------------------------------------------
# Post processing
# ---------------------------------------------------------------------------


class TestMattermostPostProcessing:
    """Tests for _process_post."""

    def test_post_enqueued(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_user_id"

        post = {
            "id": "post1",
            "user_id": "alice_id",
            "channel_id": "ch123",
            "message": "hello bot",
            "create_at": 1700000000000,
            "root_id": "",
        }

        adapter._process_post(post)

        msg = adapter._message_queue.get_nowait()
        assert msg.platform == "mattermost"
        assert msg.sender_id == "alice_id"
        assert msg.chat_id == "ch123"
        assert msg.text == "hello bot"
        assert msg.id == "post1"
        assert msg.reply_to is None

    def test_own_messages_ignored(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_user_id"

        post = {
            "id": "post2",
            "user_id": "bot_user_id",
            "channel_id": "ch123",
            "message": "my own message",
            "create_at": 1700000000000,
        }

        adapter._process_post(post)
        assert adapter._message_queue.empty()

    def test_empty_message_ignored(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_user_id"

        post = {
            "id": "post3",
            "user_id": "alice_id",
            "channel_id": "ch123",
            "message": "",
            "create_at": 1700000000000,
        }

        adapter._process_post(post)
        assert adapter._message_queue.empty()

    def test_thread_root_id_captured(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_user_id"

        post = {
            "id": "post4",
            "user_id": "bob_id",
            "channel_id": "ch123",
            "message": "threaded reply",
            "create_at": 1700000000000,
            "root_id": "post1",
        }

        adapter._process_post(post)
        msg = adapter._message_queue.get_nowait()
        assert msg.reply_to == "post1"

    def test_invalid_timestamp_handled(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_user_id"

        post = {
            "id": "post5",
            "user_id": "alice_id",
            "channel_id": "ch123",
            "message": "test",
            "create_at": -999999999999999,
        }

        adapter._process_post(post)
        msg = adapter._message_queue.get_nowait()
        assert msg.text == "test"


# ---------------------------------------------------------------------------
# WebSocket event handling
# ---------------------------------------------------------------------------


class TestMattermostWSEventHandling:
    """Tests for _handle_ws_event."""

    def test_posted_event_processed(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_user_id"

        post = {
            "id": "post1",
            "user_id": "alice_id",
            "channel_id": "ch1",
            "message": "ws message",
            "create_at": 1700000000000,
        }

        ws_event = {
            "event": "posted",
            "data": {"post": json.dumps(post)},
        }

        adapter._handle_ws_event(ws_event)
        msg = adapter._message_queue.get_nowait()
        assert msg.text == "ws message"

    def test_non_posted_event_ignored(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        ws_event = {"event": "typing", "data": {}}
        adapter._handle_ws_event(ws_event)
        assert adapter._message_queue.empty()

    def test_invalid_post_json_ignored(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        ws_event = {
            "event": "posted",
            "data": {"post": "not valid json{{{"},
        }
        adapter._handle_ws_event(ws_event)
        assert adapter._message_queue.empty()

    def test_empty_post_string_ignored(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        ws_event = {"event": "posted", "data": {"post": ""}}
        adapter._handle_ws_event(ws_event)
        assert adapter._message_queue.empty()


# ---------------------------------------------------------------------------
# Connect / Disconnect
# ---------------------------------------------------------------------------


class TestMattermostConnectDisconnect:
    """Tests for connect and disconnect lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_resolves_user_id(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")

        me_resp = MagicMock()
        me_resp.status_code = 200
        me_resp.json.return_value = {"id": "bot123"}

        from unittest.mock import patch

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=me_resp)
            mock_client.aclose = AsyncMock()
            mock_cls.return_value = mock_client

            await adapter.connect()

        assert adapter._user_id == "bot123"
        assert adapter._connected is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_connect_raises_on_auth_failure(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="bad")

        fail_resp = MagicMock()
        fail_resp.status_code = 401
        fail_resp.text = "Unauthorized"

        from unittest.mock import patch

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=fail_resp)
            mock_client.aclose = AsyncMock()
            mock_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="Mattermost auth failed"):
                await adapter.connect()

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        await adapter.disconnect()
        assert adapter._connected is False


# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------


class TestMattermostListen:
    """Tests for the listen async iterator."""

    @pytest.mark.asyncio
    async def test_listen_yields_enqueued_messages(self) -> None:
        adapter = MattermostAdapter(url="https://chat.example.com", token="tok")
        adapter._user_id = "bot_user_id"

        post = {
            "id": "post1",
            "user_id": "alice_id",
            "channel_id": "ch1",
            "message": "hi there",
            "create_at": 1700000000000,
        }
        adapter._process_post(post)

        messages: list = []
        async for msg in adapter.listen():
            messages.append(msg)
            break

        assert len(messages) == 1
        assert messages[0].text == "hi there"
