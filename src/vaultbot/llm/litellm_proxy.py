"""LiteLLM proxy integration as universal LLM gateway."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.llm.compatible import CompatibleProvider
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class LiteLLMConfig:
    """LiteLLM proxy configuration."""

    proxy_url: str = "http://localhost:4000"
    api_key: str = ""
    default_model: str = "gpt-4o"
    model_aliases: dict[str, str] = field(default_factory=dict)
    fallback_models: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def resolve_model(self, model: str) -> str:
        return self.model_aliases.get(model, model)


class LiteLLMProxyProvider:
    """LiteLLM proxy provider for universal model access."""

    def __init__(self, config: LiteLLMConfig | None = None) -> None:
        self._config = config or LiteLLMConfig()
        self._inner = CompatibleProvider(
            base_url=self._config.proxy_url,
            default_model=self._config.default_model,
            api_key=self._config.api_key or "not-needed",
            provider_label="litellm",
        )

    @property
    def provider_name(self) -> str:
        return "litellm"

    @property
    def config(self) -> LiteLLMConfig:
        return self._config

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        resolved = self._config.resolve_model(model) if model else None
        return await self._inner.complete(
            messages,
            model=resolved,
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
        resolved = self._config.resolve_model(model) if model else None
        async for chunk in self._inner.stream(
            messages,
            model=resolved,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk

    async def close(self) -> None:
        await self._inner.close()
