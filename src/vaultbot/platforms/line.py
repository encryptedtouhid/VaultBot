"""LINE messaging platform adapter.

Implements an async LINE bot using the Messaging API via ``httpx``.
Supports webhook-based message receiving and reply/push message sending.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import base64
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_BASE = "https://api.line.me/v2/bot"
_REPLY = f"{_API_BASE}/message/reply"
_PUSH = f"{_API_BASE}/message/push"
_PROFILE = f"{_API_BASE}/profile"


class LineAdapter:
    """LINE bot adapter using the Messaging API.

    Parameters
    ----------
    channel_access_token:
        Long-lived channel access token from LINE Developers Console.
    channel_secret:
        Channel secret for webhook signature verification.
    """

    def __init__(
        self,
        *,
        channel_access_token: str,
        channel_secret: str = "",
    ) -> None:
        self._token = channel_access_token
        self._secret = channel_secret
        self._client: httpx.AsyncClient | None = None
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._connected = False
        self._reply_tokens: dict[str, str] = {}

    @property
    def platform_name(self) -> str:
        return "line"

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)
        self._connected = True
        logger.info("line_connected")

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info("line_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        if not self._client:
            raise RuntimeError("LINE adapter not connected")

        reply_token = self._reply_tokens.pop(message.chat_id, None)

        msg_body = [{"type": "text", "text": message.text}]

        if reply_token:
            await self._client.post(
                _REPLY,
                json={"replyToken": reply_token, "messages": msg_body},
                headers=self._auth_headers(),
            )
        else:
            await self._client.post(
                _PUSH,
                json={"to": message.chat_id, "messages": msg_body},
                headers=self._auth_headers(),
            )

    async def healthcheck(self) -> bool:
        if not self._client:
            return False
        try:
            resp = await self._client.get(
                f"{_API_BASE}/info",
                headers=self._auth_headers(),
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def verify_signature(self, body: bytes, signature: str) -> bool:
        if not self._secret:
            return True
        digest = hmac.new(
            self._secret.encode("utf-8"), body, hashlib.sha256
        ).digest()
        return hmac.compare_digest(base64.b64encode(digest).decode("utf-8"), signature)

    def handle_webhook(self, payload: dict) -> None:
        events = payload.get("events", [])
        for event in events:
            if event.get("type") != "message":
                continue
            msg = event.get("message", {})
            if msg.get("type") != "text":
                continue

            source = event.get("source", {})
            user_id = source.get("userId", "unknown")
            chat_id = source.get("groupId") or source.get("roomId") or user_id

            reply_token = event.get("replyToken", "")
            if reply_token:
                self._reply_tokens[chat_id] = reply_token

            ts = event.get("timestamp", 0)
            try:
                timestamp = datetime.fromtimestamp(ts / 1000, tz=UTC)
            except (ValueError, OSError, OverflowError):
                timestamp = datetime.now(UTC)

            inbound = InboundMessage(
                id=msg.get("id", ""),
                platform="line",
                sender_id=user_id,
                chat_id=chat_id,
                text=msg.get("text", ""),
                timestamp=timestamp,
                raw=event,
            )
            self._message_queue.put_nowait(inbound)
