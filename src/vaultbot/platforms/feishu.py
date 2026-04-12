"""Feishu (Lark) messaging platform adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://open.feishu.cn/open-apis"


class FeishuAdapter:
    """Feishu/Lark platform adapter."""

    def __init__(self, app_id: str, app_secret: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._client = httpx.AsyncClient(base_url=_API_URL, timeout=30.0)
        self._access_token: str = ""
        self._running = False

    @property
    def platform_name(self) -> str:
        return "feishu"

    async def connect(self) -> None:
        resp = await self._client.post(
            "/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret},
        )
        resp.raise_for_status()
        self._access_token = resp.json().get("tenant_access_token", "")
        self._running = True
        logger.info("feishu_connected")

    async def disconnect(self) -> None:
        self._running = False
        await self._client.aclose()
        logger.info("feishu_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while self._running:
            yield InboundMessage(platform="feishu", user_id="", content="")
            return

    async def send(self, message: OutboundMessage) -> None:
        await self._client.post(
            "/im/v1/messages",
            json={"receive_id": message.chat_id, "msg_type": "text", "content": message.content},
            headers={"Authorization": f"Bearer {self._access_token}"},
        )

    async def healthcheck(self) -> bool:
        return self._running and bool(self._access_token)
