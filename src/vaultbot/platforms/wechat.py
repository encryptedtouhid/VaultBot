"""WeChat Official Account platform adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.weixin.qq.com/cgi-bin"


class WeChatAdapter:
    """WeChat Official Account platform adapter."""

    def __init__(self, app_id: str, app_secret: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._client = httpx.AsyncClient(base_url=_API_URL, timeout=30.0)
        self._access_token: str = ""
        self._running = False

    @property
    def platform_name(self) -> str:
        return "wechat"

    async def connect(self) -> None:
        resp = await self._client.get(
            "/token",
            params={
                "grant_type": "client_credential",
                "appid": self._app_id,
                "secret": self._app_secret,
            },
        )
        resp.raise_for_status()
        self._access_token = resp.json().get("access_token", "")
        self._running = True
        logger.info("wechat_connected")

    async def disconnect(self) -> None:
        self._running = False
        await self._client.aclose()

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while self._running:
            yield InboundMessage(platform="wechat", user_id="", content="")
            return

    async def send(self, message: OutboundMessage) -> None:
        await self._client.post(
            f"/message/custom/send?access_token={self._access_token}",
            json={
                "touser": message.chat_id,
                "msgtype": "text",
                "text": {"content": message.content},
            },
        )

    async def healthcheck(self) -> bool:
        return self._running and bool(self._access_token)
