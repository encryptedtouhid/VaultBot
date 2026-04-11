"""Google Chat messaging platform adapter.

Implements an async Google Chat bot using the Google Chat API via ``httpx``.
Supports webhook-based message receiving and REST API message sending.
Uses service account authentication.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_BASE = "https://chat.googleapis.com/v1"


class GoogleChatAdapter:
    """Google Chat bot adapter using the Chat API.

    Parameters
    ----------
    service_account_key:
        JSON string or dict of the service account credentials.
    webhook_url:
        Optional incoming webhook URL for simple message sending.
    """

    def __init__(
        self,
        *,
        service_account_key: str = "",
        webhook_url: str = "",
    ) -> None:
        self._service_account_key = service_account_key
        self._webhook_url = webhook_url
        self._client: httpx.AsyncClient | None = None
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._connected = False
        self._access_token: str = ""

    @property
    def platform_name(self) -> str:
        return "googlechat"

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)
        self._connected = True
        logger.info("googlechat_connected")

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info("googlechat_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        if not self._client:
            raise RuntimeError("Google Chat adapter not connected")

        if self._webhook_url:
            await self._client.post(
                self._webhook_url,
                json={"text": message.text},
            )
        else:
            url = f"{_API_BASE}/{message.chat_id}/messages"
            await self._client.post(
                url,
                json={"text": message.text},
                headers=self._auth_headers(),
            )

    async def healthcheck(self) -> bool:
        return self._connected and self._client is not None

    def _auth_headers(self) -> dict[str, str]:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    def handle_webhook(self, payload: dict) -> None:
        msg_type = payload.get("type", "")
        if msg_type != "MESSAGE":
            return

        message = payload.get("message", {})
        text = message.get("argumentText", "") or message.get("text", "")
        if not text:
            return

        sender = message.get("sender", {})
        user_id = sender.get("name", "unknown")
        space = payload.get("space", {})
        chat_id = space.get("name", "unknown")

        create_time = message.get("createTime", "")
        try:
            timestamp = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now(UTC)

        inbound = InboundMessage(
            id=message.get("name", ""),
            platform="googlechat",
            sender_id=user_id,
            chat_id=chat_id,
            text=text.strip(),
            timestamp=timestamp,
            reply_to=message.get("thread", {}).get("name"),
            raw=payload,
        )
        self._message_queue.put_nowait(inbound)
