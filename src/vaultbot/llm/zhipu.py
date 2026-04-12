"""Zhipu AI (GLM) LLM provider."""

from __future__ import annotations

from collections.abc import AsyncIterator

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.llm.compatible import CompatibleProvider

_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
_DEFAULT_MODEL = "glm-4"


class ZhipuProvider:
    """Zhipu AI GLM provider via OpenAI-compatible API."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._inner = CompatibleProvider(
            base_url=_BASE_URL,
            default_model=model,
            api_key=api_key,
            provider_label="zhipu",
        )

    @property
    def provider_name(self) -> str:
        return "zhipu"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        return await self._inner.complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        async for chunk in self._inner.stream(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk

    async def close(self) -> None:
        await self._inner.close()
