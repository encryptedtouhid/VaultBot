"""QQ Bot messaging platform adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.sgroup.qq.com"
_SANDBOX_API_URL = "https://sandbox.api.sgroup.qq.com"


class QQBotAdapter:
    """QQ Bot platform adapter using the QQ Bot Open Platform API."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        sandbox: bool = False,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        base_url = _SANDBOX_API_URL if sandbox else _API_URL
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self._access_token: str = ""
        self._running = False

    @property
    def platform_name(self) -> str:
        return "qq"

    async def connect(self) -> None:
        resp = await self._client.post(
            "/app/getAppAccessToken",
            json={"appId": self._app_id, "clientSecret": self._app_secret},
        )
        resp.raise_for_status()
        self._access_token = resp.json().get("access_token", "")
        self._running = True
        logger.info("qq_connected")

    async def disconnect(self) -> None:
        self._running = False
        await self._client.aclose()
        logger.info("qq_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while self._running:
            yield InboundMessage(platform="qq", user_id="", content="")
            return

    async def send(self, message: OutboundMessage) -> None:
        await self._client.post(
            f"/v2/groups/{message.chat_id}/messages",
            json={"content": message.content, "msg_type": 0},
            headers={"Authorization": f"QQBot {self._access_token}"},
        )

    async def healthcheck(self) -> bool:
        return self._running and bool(self._access_token)
