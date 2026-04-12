"""Zalo Official Account platform adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://openapi.zalo.me/v3.0"


class ZaloAdapter:
    """Zalo Official Account platform adapter."""

    def __init__(self, access_token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=_API_URL,
            timeout=30.0,
            headers={"access_token": access_token},
        )
        self._running = False

    @property
    def platform_name(self) -> str:
        return "zalo"

    async def connect(self) -> None:
        self._running = True
        logger.info("zalo_connected")

    async def disconnect(self) -> None:
        self._running = False
        await self._client.aclose()

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while self._running:
            yield InboundMessage(platform="zalo", user_id="", content="")
            return

    async def send(self, message: OutboundMessage) -> None:
        await self._client.post(
            "/oa/message/cs",
            json={
                "recipient": {"user_id": message.chat_id},
                "message": {"text": message.content},
            },
        )

    async def healthcheck(self) -> bool:
        return self._running
