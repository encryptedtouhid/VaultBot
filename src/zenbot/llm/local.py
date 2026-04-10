"""Local LLM provider adapter for Ollama, vLLM, and other OpenAI-compatible servers."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from zenbot.core.message import ChatMessage
from zenbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from zenbot.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434/v1"  # Ollama default
DEFAULT_MODEL = "llama3.2"


class LocalProvider:
    """LLM provider for local models via OpenAI-compatible API.

    Works with:
    - Ollama (default, http://localhost:11434/v1)
    - vLLM (http://localhost:8000/v1)
    - llama.cpp server (http://localhost:8080/v1)
    - Any OpenAI-compatible endpoint
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        default_model: str = DEFAULT_MODEL,
        api_key: str = "not-needed",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,  # Local models can be slow
        )

    @property
    def provider_name(self) -> str:
        return "local"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Generate a completion using the local model."""
        api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        response = await self._client.post(
            "/chat/completions",
            json={
                "model": model or self._default_model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", model or self._default_model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", ""),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        """Stream a completion using the local model."""
        api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        async with self._client.stream(
            "POST",
            "/chat/completions",
            json={
                "model": model or self._default_model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    yield LLMChunk(content="", is_final=True)
                    return

                import json

                data = json.loads(data_str)
                if data["choices"] and data["choices"][0].get("delta", {}).get(
                    "content"
                ):
                    yield LLMChunk(content=data["choices"][0]["delta"]["content"])

        yield LLMChunk(content="", is_final=True)
