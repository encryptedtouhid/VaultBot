"""Zulip platform adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ZulipAdapter:
    """Zulip platform adapter."""

    def __init__(self, server_url: str, email: str, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=server_url.rstrip("/") + "/api/v1",
            timeout=30.0,
            auth=(email, api_key),
        )
        self._running = False

    @property
    def platform_name(self) -> str:
        return "zulip"

    async def connect(self) -> None:
        resp = await self._client.get("/users/me")
        resp.raise_for_status()
        self._running = True
        logger.info("zulip_connected")

    async def disconnect(self) -> None:
        self._running = False
        await self._client.aclose()

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while self._running:
            yield InboundMessage(platform="zulip", user_id="", content="")
            return

    async def send(self, message: OutboundMessage) -> None:
        await self._client.post(
            "/messages",
            data={"type": "direct", "to": message.chat_id, "content": message.content},
        )

    async def healthcheck(self) -> bool:
        return self._running
