"""OpenAI GPT LLM provider adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import openai

from zenbot.core.message import ChatMessage
from zenbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from zenbot.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider:
    """LLM provider using OpenAI's GPT API."""

    def __init__(self, api_key: str, default_model: str = DEFAULT_MODEL) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._default_model = default_model

    @property
    def provider_name(self) -> str:
        return "openai"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Generate a completion using OpenAI GPT."""
        api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        response = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=api_messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not response.choices:
            raise RuntimeError("OpenAI returned empty choices array")
        choice = response.choices[0]
        content = choice.message.content or ""

        return LLMResponse(
            content=content,
            model=response.model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            finish_reason=choice.finish_reason or "",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        """Stream a completion using OpenAI GPT."""
        api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        stream = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=api_messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield LLMChunk(content=chunk.choices[0].delta.content)

        yield LLMChunk(content="", is_final=True)
