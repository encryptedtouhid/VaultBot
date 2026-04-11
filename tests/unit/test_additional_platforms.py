"""Unit tests for LINE, Google Chat, Twitch, and Nostr platform adapters."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vaultbot.core.message import OutboundMessage


# ==========================================================================
# LINE Adapter Tests
# ==========================================================================


class TestLineAdapterInit:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")
        assert adapter.platform_name == "line"

    def test_initial_state(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")
        assert adapter._connected is False


class TestLineHealthcheck:
    @pytest.mark.asyncio
    async def test_unhealthy_when_disconnected(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")
        assert await adapter.healthcheck() is False


class TestLineWebhook:
    def test_text_message_enqueued(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")

        payload = {
            "events": [{
                "type": "message",
                "replyToken": "rtoken1",
                "source": {"userId": "user1", "type": "user"},
                "timestamp": 1700000000000,
                "message": {"id": "msg1", "type": "text", "text": "hello"},
            }]
        }
        adapter.handle_webhook(payload)

        msg = adapter._message_queue.get_nowait()
        assert msg.platform == "line"
        assert msg.sender_id == "user1"
        assert msg.text == "hello"

    def test_non_text_message_ignored(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")

        payload = {
            "events": [{
                "type": "message",
                "source": {"userId": "user1"},
                "timestamp": 0,
                "message": {"id": "msg2", "type": "image"},
            }]
        }
        adapter.handle_webhook(payload)
        assert adapter._message_queue.empty()

    def test_non_message_event_ignored(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")

        payload = {"events": [{"type": "follow", "source": {"userId": "user1"}}]}
        adapter.handle_webhook(payload)
        assert adapter._message_queue.empty()

    def test_group_chat_id(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")

        payload = {
            "events": [{
                "type": "message",
                "source": {"userId": "user1", "groupId": "group123"},
                "timestamp": 0,
                "message": {"id": "msg3", "type": "text", "text": "group msg"},
            }]
        }
        adapter.handle_webhook(payload)
        msg = adapter._message_queue.get_nowait()
        assert msg.chat_id == "group123"

    def test_reply_token_stored(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")

        payload = {
            "events": [{
                "type": "message",
                "replyToken": "rtoken_xyz",
                "source": {"userId": "user1"},
                "timestamp": 0,
                "message": {"id": "msg4", "type": "text", "text": "hi"},
            }]
        }
        adapter.handle_webhook(payload)
        assert "user1" in adapter._reply_tokens


class TestLineSend:
    @pytest.mark.asyncio
    async def test_send_raises_when_not_connected(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.send(OutboundMessage(chat_id="user1", text="hi"))

    @pytest.mark.asyncio
    async def test_send_uses_reply_when_available(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client
        adapter._reply_tokens["user1"] = "rtoken"

        await adapter.send(OutboundMessage(chat_id="user1", text="reply"))

        call_args = mock_client.post.call_args
        assert "reply" in call_args[0][0]  # reply URL

    @pytest.mark.asyncio
    async def test_send_uses_push_when_no_reply_token(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok")
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_resp)
        adapter._client = mock_client

        await adapter.send(OutboundMessage(chat_id="user1", text="push"))

        call_args = mock_client.post.call_args
        assert "push" in call_args[0][0]


class TestLineSignature:
    def test_verify_signature_no_secret(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok", channel_secret="")
        assert adapter.verify_signature(b"body", "anysig") is True

    def test_verify_signature_valid(self) -> None:
        import base64, hashlib, hmac as hmac_mod
        from vaultbot.platforms.line import LineAdapter
        secret = "test_secret"
        body = b'{"events":[]}'
        digest = hmac_mod.new(secret.encode(), body, hashlib.sha256).digest()
        sig = base64.b64encode(digest).decode()

        adapter = LineAdapter(channel_access_token="tok", channel_secret=secret)
        assert adapter.verify_signature(body, sig) is True

    def test_verify_signature_invalid(self) -> None:
        from vaultbot.platforms.line import LineAdapter
        adapter = LineAdapter(channel_access_token="tok", channel_secret="secret")
        assert adapter.verify_signature(b"body", "invalidsig") is False


# ==========================================================================
# Google Chat Adapter Tests
# ==========================================================================


class TestGoogleChatAdapterInit:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter()
        assert adapter.platform_name == "googlechat"

    def test_initial_state(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter()
        assert adapter._connected is False


class TestGoogleChatHealthcheck:
    @pytest.mark.asyncio
    async def test_healthy_when_connected(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter()
        adapter._connected = True
        adapter._client = AsyncMock()
        assert await adapter.healthcheck() is True

    @pytest.mark.asyncio
    async def test_unhealthy_when_disconnected(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter()
        assert await adapter.healthcheck() is False


class TestGoogleChatWebhook:
    def test_message_event_enqueued(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter()

        payload = {
            "type": "MESSAGE",
            "message": {
                "name": "spaces/s1/messages/m1",
                "text": "@bot hello",
                "argumentText": "hello",
                "sender": {"name": "users/user1"},
                "createTime": "2024-01-01T00:00:00Z",
                "thread": {"name": "spaces/s1/threads/t1"},
            },
            "space": {"name": "spaces/s1"},
        }
        adapter.handle_webhook(payload)

        msg = adapter._message_queue.get_nowait()
        assert msg.platform == "googlechat"
        assert msg.sender_id == "users/user1"
        assert msg.chat_id == "spaces/s1"
        assert msg.text == "hello"
        assert msg.reply_to == "spaces/s1/threads/t1"

    def test_non_message_event_ignored(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter()

        payload = {"type": "ADDED_TO_SPACE", "space": {"name": "spaces/s1"}}
        adapter.handle_webhook(payload)
        assert adapter._message_queue.empty()

    def test_empty_text_ignored(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter()

        payload = {
            "type": "MESSAGE",
            "message": {"name": "m1", "text": "", "sender": {"name": "u1"}, "createTime": ""},
            "space": {"name": "s1"},
        }
        adapter.handle_webhook(payload)
        assert adapter._message_queue.empty()


class TestGoogleChatSend:
    @pytest.mark.asyncio
    async def test_send_raises_when_not_connected(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter()
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.send(OutboundMessage(chat_id="spaces/s1", text="hi"))

    @pytest.mark.asyncio
    async def test_send_via_webhook_url(self) -> None:
        from vaultbot.platforms.googlechat import GoogleChatAdapter
        adapter = GoogleChatAdapter(webhook_url="https://hooks.example.com/chat")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
        adapter._client = mock_client

        await adapter.send(OutboundMessage(chat_id="spaces/s1", text="hello"))
        call_args = mock_client.post.call_args
        assert "hooks.example.com" in call_args[0][0]


# ==========================================================================
# Twitch Adapter Tests
# ==========================================================================


class TestTwitchAdapterInit:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        assert adapter.platform_name == "twitch"

    def test_oauth_prefix_added(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="mytoken", nick="bot")
        assert adapter._token == "oauth:mytoken"

    def test_oauth_prefix_not_doubled(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="oauth:mytoken", nick="bot")
        assert adapter._token == "oauth:mytoken"

    def test_nick_lowered(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="MyBot")
        assert adapter._nick == "mybot"

    def test_channels_lowered_and_stripped(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot", channels=["#MyChannel"])
        assert adapter._channels == ["mychannel"]


class TestTwitchHealthcheck:
    @pytest.mark.asyncio
    async def test_unhealthy_when_disconnected(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        assert await adapter.healthcheck() is False

    @pytest.mark.asyncio
    async def test_healthy_when_connected(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        adapter._connected = True
        writer = MagicMock()
        writer.is_closing.return_value = False
        adapter._writer = writer
        assert await adapter.healthcheck() is True


class TestTwitchLineHandling:
    @pytest.mark.asyncio
    async def test_ping_pong(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        adapter._writer = writer

        await adapter._handle_line("PING :tmi.twitch.tv")
        written = writer.write.call_args[0][0].decode("utf-8")
        assert "PONG :tmi.twitch.tv" in written

    @pytest.mark.asyncio
    async def test_privmsg_enqueued(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        adapter._nick = "bot"

        await adapter._handle_line(":alice!alice@alice.tmi.twitch.tv PRIVMSG #channel :hello bot")
        msg = adapter._message_queue.get_nowait()
        assert msg.platform == "twitch"
        assert msg.sender_id == "alice"
        assert msg.chat_id == "#channel"
        assert msg.text == "hello bot"

    @pytest.mark.asyncio
    async def test_privmsg_with_tags(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")

        line = "@badge-info=;badges=;color=#FF0000 :alice!a@a.tmi.twitch.tv PRIVMSG #ch :tagged msg"
        await adapter._handle_line(line)
        msg = adapter._message_queue.get_nowait()
        assert msg.text == "tagged msg"

    @pytest.mark.asyncio
    async def test_self_messages_ignored(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")

        await adapter._handle_line(":bot!bot@bot.tmi.twitch.tv PRIVMSG #ch :my msg")
        assert adapter._message_queue.empty()


class TestTwitchSend:
    @pytest.mark.asyncio
    async def test_send_raises_when_not_connected(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.send(OutboundMessage(chat_id="#ch", text="hi"))

    @pytest.mark.asyncio
    async def test_send_adds_hash_prefix(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        adapter._writer = writer

        await adapter.send(OutboundMessage(chat_id="mychannel", text="hello"))
        written = writer.write.call_args[0][0].decode("utf-8")
        assert "PRIVMSG #mychannel :hello" in written


class TestTwitchDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self) -> None:
        from vaultbot.platforms.twitch import TwitchAdapter
        adapter = TwitchAdapter(oauth_token="tok", nick="bot")
        await adapter.disconnect()
        assert adapter._connected is False


# ==========================================================================
# Nostr Adapter Tests
# ==========================================================================


class TestNostrAdapterInit:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="abc123")
        assert adapter.platform_name == "nostr"

    def test_default_relay(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="abc123")
        assert "wss://relay.damus.io" in adapter._relays


class TestNostrHealthcheck:
    @pytest.mark.asyncio
    async def test_unhealthy_when_disconnected(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="abc123")
        assert await adapter.healthcheck() is False


class TestNostrEventProcessing:
    def test_text_note_enqueued(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="mypubkey")

        event = {
            "id": "event1",
            "pubkey": "sender_pubkey",
            "created_at": 1700000000,
            "kind": 1,
            "tags": [],
            "content": "hello nostr",
        }
        adapter._process_event(event)

        msg = adapter._message_queue.get_nowait()
        assert msg.platform == "nostr"
        assert msg.sender_id == "sender_pubkey"
        assert msg.text == "hello nostr"

    def test_own_events_ignored(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="mypubkey")

        event = {"id": "e2", "pubkey": "mypubkey", "created_at": 0, "kind": 1, "content": "own", "tags": []}
        adapter._process_event(event)
        assert adapter._message_queue.empty()

    def test_empty_content_ignored(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="mypubkey")

        event = {"id": "e3", "pubkey": "other", "created_at": 0, "kind": 1, "content": "", "tags": []}
        adapter._process_event(event)
        assert adapter._message_queue.empty()

    def test_reply_tag_extracted(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="mypubkey")

        event = {
            "id": "e4", "pubkey": "other", "created_at": 0, "kind": 1,
            "content": "reply", "tags": [["e", "parent_event_id"]],
        }
        adapter._process_event(event)
        msg = adapter._message_queue.get_nowait()
        assert msg.reply_to == "parent_event_id"


class TestNostrBuildEvent:
    def test_event_has_required_fields(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="abc123")

        event = adapter._build_event(kind=1, content="test", tags=[])
        assert event["pubkey"] == "abc123"
        assert event["kind"] == 1
        assert event["content"] == "test"
        assert "id" in event
        assert len(event["id"]) == 64  # SHA-256 hex


class TestNostrConnect:
    @pytest.mark.asyncio
    async def test_connect_requires_pubkey(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="")
        with pytest.raises(ValueError, match="public_key_hex"):
            await adapter.connect()

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="abc")
        await adapter.disconnect()
        assert adapter._connected is False


class TestNostrSend:
    @pytest.mark.asyncio
    async def test_send_raises_when_not_connected(self) -> None:
        from vaultbot.platforms.nostr import NostrAdapter
        adapter = NostrAdapter(public_key_hex="abc")
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.send(OutboundMessage(chat_id="target", text="hi"))
