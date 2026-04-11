"""Unit tests for the Matrix platform adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vaultbot.core.message import OutboundMessage
from vaultbot.platforms.matrix import MatrixAdapter

# ---------------------------------------------------------------------------
# Construction / properties
# ---------------------------------------------------------------------------


class TestMatrixAdapterInit:
    """Tests for MatrixAdapter construction and properties."""

    def test_platform_name(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        assert adapter.platform_name == "matrix"

    def test_homeserver_trailing_slash_stripped(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org/", access_token="tok")
        assert adapter._homeserver == "https://matrix.org"

    def test_initial_state_not_connected(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        assert adapter._connected is False

    def test_rooms_default_empty(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        assert adapter._rooms == []

    def test_rooms_stored(self) -> None:
        adapter = MatrixAdapter(
            homeserver="https://matrix.org",
            access_token="tok",
            rooms=["!room1:matrix.org", "#general:matrix.org"],
        )
        assert len(adapter._rooms) == 2

    def test_txn_counter_starts_at_zero(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        assert adapter._txn_counter == 0


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------


class TestMatrixHealthcheck:
    """Tests for the healthcheck method."""

    @pytest.mark.asyncio
    async def test_unhealthy_when_disconnected(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        assert await adapter.healthcheck() is False

    @pytest.mark.asyncio
    async def test_healthy_when_whoami_succeeds(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        assert await adapter.healthcheck() is True

    @pytest.mark.asyncio
    async def test_unhealthy_when_whoami_fails(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 401

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        assert await adapter.healthcheck() is False

    @pytest.mark.asyncio
    async def test_unhealthy_on_exception(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("connection lost"))
        adapter._client = mock_client

        assert await adapter.healthcheck() is False


# ---------------------------------------------------------------------------
# URL / headers helpers
# ---------------------------------------------------------------------------


class TestMatrixHelpers:
    """Tests for internal helper methods."""

    def test_url_building(self) -> None:
        adapter = MatrixAdapter(homeserver="https://example.com", access_token="tok")
        assert adapter._url("/test") == "https://example.com/test"

    def test_auth_headers(self) -> None:
        adapter = MatrixAdapter(homeserver="https://example.com", access_token="my_token")
        headers = adapter._auth_headers()
        assert headers["Authorization"] == "Bearer my_token"


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------


class TestMatrixSend:
    """Tests for sending messages."""

    @pytest.mark.asyncio
    async def test_send_raises_when_not_connected(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="")
        msg = OutboundMessage(chat_id="!room:matrix.org", text="hello")
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.send(msg)

    @pytest.mark.asyncio
    async def test_send_puts_message(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        msg = OutboundMessage(chat_id="!room:matrix.org", text="hello world")
        await adapter.send(msg)

        mock_client.put.assert_called_once()
        call_kwargs = mock_client.put.call_args
        assert "m.room.message" in call_kwargs[0][0]
        assert call_kwargs[1]["json"]["body"] == "hello world"
        assert call_kwargs[1]["json"]["msgtype"] == "m.text"

    @pytest.mark.asyncio
    async def test_send_increments_txn_counter(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        msg = OutboundMessage(chat_id="!room:matrix.org", text="msg1")
        await adapter.send(msg)
        assert adapter._txn_counter == 1

        await adapter.send(msg)
        assert adapter._txn_counter == 2

    @pytest.mark.asyncio
    async def test_send_logs_error_on_failure(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        msg = OutboundMessage(chat_id="!room:matrix.org", text="test")
        # Should not raise, just log
        await adapter.send(msg)


# ---------------------------------------------------------------------------
# Event processing
# ---------------------------------------------------------------------------


class TestMatrixEventProcessing:
    """Tests for _process_event."""

    def test_text_message_enqueued(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        adapter._user_id = "@vaultbot:matrix.org"

        event = {
            "type": "m.room.message",
            "event_id": "$event1",
            "sender": "@alice:matrix.org",
            "origin_server_ts": 1700000000000,
            "content": {
                "msgtype": "m.text",
                "body": "hello bot",
            },
        }

        adapter._process_event("!room:matrix.org", event)

        msg = adapter._message_queue.get_nowait()
        assert msg.platform == "matrix"
        assert msg.sender_id == "@alice:matrix.org"
        assert msg.chat_id == "!room:matrix.org"
        assert msg.text == "hello bot"
        assert msg.id == "$event1"

    def test_own_messages_ignored(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        adapter._user_id = "@vaultbot:matrix.org"

        event = {
            "type": "m.room.message",
            "event_id": "$event2",
            "sender": "@vaultbot:matrix.org",
            "origin_server_ts": 1700000000000,
            "content": {"msgtype": "m.text", "body": "my own msg"},
        }

        adapter._process_event("!room:matrix.org", event)
        assert adapter._message_queue.empty()

    def test_non_text_msgtype_ignored(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        adapter._user_id = "@vaultbot:matrix.org"

        event = {
            "type": "m.room.message",
            "event_id": "$event3",
            "sender": "@alice:matrix.org",
            "origin_server_ts": 1700000000000,
            "content": {"msgtype": "m.image", "body": "photo.jpg"},
        }

        adapter._process_event("!room:matrix.org", event)
        assert adapter._message_queue.empty()

    def test_non_message_event_ignored(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        adapter._user_id = "@vaultbot:matrix.org"

        event = {
            "type": "m.room.member",
            "event_id": "$event4",
            "sender": "@alice:matrix.org",
            "content": {"membership": "join"},
        }

        adapter._process_event("!room:matrix.org", event)
        assert adapter._message_queue.empty()

    def test_empty_body_ignored(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        adapter._user_id = "@vaultbot:matrix.org"

        event = {
            "type": "m.room.message",
            "event_id": "$event5",
            "sender": "@alice:matrix.org",
            "origin_server_ts": 1700000000000,
            "content": {"msgtype": "m.text", "body": ""},
        }

        adapter._process_event("!room:matrix.org", event)
        assert adapter._message_queue.empty()

    def test_reply_to_extracted(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        adapter._user_id = "@vaultbot:matrix.org"

        event = {
            "type": "m.room.message",
            "event_id": "$reply1",
            "sender": "@bob:matrix.org",
            "origin_server_ts": 1700000000000,
            "content": {
                "msgtype": "m.text",
                "body": "replying",
                "m.relates_to": {
                    "m.in_reply_to": {"event_id": "$original_event"},
                },
            },
        }

        adapter._process_event("!room:matrix.org", event)
        msg = adapter._message_queue.get_nowait()
        assert msg.reply_to == "$original_event"

    def test_invalid_timestamp_handled(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        adapter._user_id = "@vaultbot:matrix.org"

        event = {
            "type": "m.room.message",
            "event_id": "$event6",
            "sender": "@alice:matrix.org",
            "origin_server_ts": -999999999999999,
            "content": {"msgtype": "m.text", "body": "test"},
        }

        adapter._process_event("!room:matrix.org", event)
        msg = adapter._message_queue.get_nowait()
        assert msg.text == "test"  # Should not crash


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestMatrixLogin:
    """Tests for the login flow."""

    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        adapter = MatrixAdapter(
            homeserver="https://matrix.org",
            user_id="@bot:matrix.org",
            password="secret",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "new_token_123",
            "user_id": "@bot:matrix.org",
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        await adapter._login()

        assert adapter._access_token == "new_token_123"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_failure_raises(self) -> None:
        adapter = MatrixAdapter(
            homeserver="https://matrix.org",
            user_id="@bot:matrix.org",
            password="wrong",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Invalid credentials"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        with pytest.raises(RuntimeError, match="Matrix login failed"):
            await adapter._login()


# ---------------------------------------------------------------------------
# Connect / Disconnect
# ---------------------------------------------------------------------------


class TestMatrixConnectDisconnect:
    """Tests for connect and disconnect lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_requires_auth(self) -> None:
        """Connect without token or password should raise ValueError."""
        adapter = MatrixAdapter(homeserver="https://matrix.org")

        with pytest.raises(ValueError, match="access_token or user_id"):
            await adapter.connect()

    @pytest.mark.asyncio
    async def test_connect_with_token_resolves_user_id(self) -> None:
        adapter = MatrixAdapter(
            homeserver="https://matrix.org",
            access_token="tok",
        )

        whoami_resp = MagicMock()
        whoami_resp.status_code = 200
        whoami_resp.json.return_value = {"user_id": "@vaultbot:matrix.org"}

        sync_resp = MagicMock()
        sync_resp.status_code = 200
        sync_resp.json.return_value = {"next_batch": "s1", "rooms": {}}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=whoami_resp)
            mock_client.aclose = AsyncMock()
            mock_cls.return_value = mock_client

            await adapter.connect()

        assert adapter._user_id == "@vaultbot:matrix.org"
        assert adapter._connected is True

        await adapter.disconnect()
        assert adapter._connected is False

    @pytest.mark.asyncio
    async def test_connect_with_password_calls_login(self) -> None:
        adapter = MatrixAdapter(
            homeserver="https://matrix.org",
            user_id="@bot:matrix.org",
            password="secret",
        )

        login_resp = MagicMock()
        login_resp.status_code = 200
        login_resp.json.return_value = {
            "access_token": "new_tok",
            "user_id": "@bot:matrix.org",
        }

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=login_resp)
            mock_client.get = AsyncMock()
            mock_client.aclose = AsyncMock()
            mock_cls.return_value = mock_client

            await adapter.connect()

        assert adapter._access_token == "new_tok"
        assert adapter._connected is True

        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        await adapter.disconnect()
        assert adapter._connected is False

    @pytest.mark.asyncio
    async def test_connect_joins_rooms(self) -> None:
        adapter = MatrixAdapter(
            homeserver="https://matrix.org",
            access_token="tok",
            user_id="@bot:matrix.org",
            rooms=["!room1:matrix.org"],
        )

        join_resp = MagicMock()
        join_resp.status_code = 200

        whoami_resp = MagicMock()
        whoami_resp.status_code = 200
        whoami_resp.json.return_value = {"user_id": "@bot:matrix.org"}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=join_resp)
            mock_client.get = AsyncMock(return_value=whoami_resp)
            mock_client.aclose = AsyncMock()
            mock_cls.return_value = mock_client

            await adapter.connect()

        # post called for join
        join_calls = [c for c in mock_client.post.call_args_list if "join" in str(c)]
        assert len(join_calls) >= 1

        await adapter.disconnect()


# ---------------------------------------------------------------------------
# Listen iterator
# ---------------------------------------------------------------------------


class TestMatrixListen:
    """Tests for the listen async iterator."""

    @pytest.mark.asyncio
    async def test_listen_yields_enqueued_messages(self) -> None:
        adapter = MatrixAdapter(homeserver="https://matrix.org", access_token="tok")
        adapter._user_id = "@vaultbot:matrix.org"

        event = {
            "type": "m.room.message",
            "event_id": "$test1",
            "sender": "@alice:matrix.org",
            "origin_server_ts": 1700000000000,
            "content": {"msgtype": "m.text", "body": "hi there"},
        }
        adapter._process_event("!room:matrix.org", event)

        messages: list = []
        async for msg in adapter.listen():
            messages.append(msg)
            break

        assert len(messages) == 1
        assert messages[0].text == "hi there"
