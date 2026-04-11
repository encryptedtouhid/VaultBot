"""OpenAI-compatible LLM provider for any service using the OpenAI API format.

Works with any provider that exposes an OpenAI-compatible /v1/chat/completions
endpoint, including self-hosted and third-party services.

Supported services:
    - OpenRouter (https://openrouter.ai/api/v1)
    - Together AI (https://api.together.xyz/v1)
    - Groq (https://api.groq.com/openai/v1)
    - Mistral (https://api.mistral.ai/v1)
    - Perplexity (https://api.perplexity.ai)
    - DeepSeek (https://api.deepseek.com/v1)
    - Fireworks AI (https://api.fireworks.ai/inference/v1)
    - Ollama (http://localhost:11434/v1)
    - vLLM (http://localhost:8000/v1)
    - llama.cpp (http://localhost:8080/v1)
    - LM Studio (http://localhost:1234/v1)
    - Any OpenAI-compatible endpoint
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Presets for popular OpenAI-compatible providers
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-sonnet-4",
        "name": "OpenRouter",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3-70b-chat-hf",
        "name": "Together AI",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.1-70b-versatile",
        "name": "Groq",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-large-latest",
        "name": "Mistral",
    },
    "perplexity": {
        "base_url": "https://api.perplexity.ai",
        "default_model": "llama-3.1-sonar-large-128k-online",
        "name": "Perplexity",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "name": "DeepSeek",
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "default_model": "accounts/fireworks/models/llama-v3p1-70b-instruct",
        "name": "Fireworks AI",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "name": "Ollama (local)",
    },
    "vllm": {
        "base_url": "http://localhost:8000/v1",
        "default_model": "default",
        "name": "vLLM (local)",
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "default_model": "default",
        "name": "LM Studio (local)",
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "name": "xAI (Grok)",
    },
    "bedrock_compat": {
        "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com/v1",
        "default_model": "anthropic.claude-sonnet-4-20250514-v1:0",
        "name": "Amazon Bedrock (compatible)",
    },
}


class CompatibleProvider:
    """LLM provider for any OpenAI-compatible API.

    Use PROVIDER_PRESETS for quick setup with popular services,
    or pass a custom base_url for any compatible endpoint.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        default_model: str = "llama3.2",
        api_key: str = "not-needed",
        provider_label: str = "compatible",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._provider_label = provider_label

        headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"}
        if extra_headers:
            headers.update(extra_headers)

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=120.0,
        )

    @classmethod
    def from_preset(
        cls,
        preset_name: str,
        api_key: str = "not-needed",
        model: str | None = None,
    ) -> CompatibleProvider:
        """Create a provider from a named preset.

        Args:
            preset_name: One of the keys in PROVIDER_PRESETS.
            api_key: API key for the service.
            model: Override the default model.
        """
        preset = PROVIDER_PRESETS.get(preset_name)
        if preset is None:
            available = ", ".join(sorted(PROVIDER_PRESETS.keys()))
            raise ValueError(f"Unknown preset '{preset_name}'. Available: {available}")

        extra_headers: dict[str, str] = {}
        # OpenRouter requires additional headers
        if preset_name == "openrouter":
            extra_headers["HTTP-Referer"] = "https://github.com/vaultbot"
            extra_headers["X-Title"] = "VaultBot"

        return cls(
            base_url=preset["base_url"],
            default_model=model or preset["default_model"],
            api_key=api_key,
            provider_label=preset_name,
            extra_headers=extra_headers,
        )

    @property
    def provider_name(self) -> str:
        return self._provider_label

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Generate a completion using the compatible API."""
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

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"{self._provider_label} returned empty choices array")

        choice = choices[0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice.get("message", {}).get("content", ""),
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
        """Stream a completion using the compatible API."""
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

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices", [])
                if choices and choices[0].get("delta", {}).get("content"):
                    yield LLMChunk(content=choices[0]["delta"]["content"])

        yield LLMChunk(content="", is_final=True)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
