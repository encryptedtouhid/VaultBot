"""Claude (Anthropic) LLM provider adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import anthropic

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class ClaudeProvider:
    """LLM provider using Anthropic's Claude API."""

    def __init__(self, api_key: str, default_model: str = DEFAULT_MODEL) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._default_model = default_model

    @property
    def provider_name(self) -> str:
        return "claude"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Generate a completion using Claude."""
        system_prompt = ""
        api_messages: list[dict[str, str]] = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        kwargs: dict[str, object] = {
            "model": model or self._default_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)  # type: ignore[arg-type]

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason or "",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        """Stream a completion using Claude."""
        system_prompt = ""
        api_messages: list[dict[str, str]] = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        kwargs: dict[str, object] = {
            "model": model or self._default_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with self._client.messages.stream(**kwargs) as stream:  # type: ignore[arg-type]
            async for text in stream.text_stream:
                yield LLMChunk(content=text)
            yield LLMChunk(content="", is_final=True)
