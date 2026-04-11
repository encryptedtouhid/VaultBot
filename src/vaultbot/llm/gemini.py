"""Google Gemini LLM provider using the Gemini REST API.

Unlike other providers that use the OpenAI-compatible format, Gemini has
its own API schema at ``generativelanguage.googleapis.com``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider:
    """Google Gemini LLM provider.

    Parameters
    ----------
    api_key:
        Gemini API key from Google AI Studio.
    default_model:
        Default model to use (e.g. ``gemini-2.0-flash``, ``gemini-1.5-pro``).
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gemini-2.0-flash",
    ) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._client = httpx.AsyncClient(timeout=120.0)

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Generate a completion using the Gemini API."""
        model_name = model or self._default_model
        url = f"{_API_BASE}/models/{model_name}:generateContent?key={self._api_key}"

        # Convert to Gemini format
        contents = self._convert_messages(messages)

        body: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        response = await self._client.post(url, json=body)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates")

        content_parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in content_parts)

        usage = data.get("usageMetadata", {})

        return LLMResponse(
            content=text,
            model=model_name,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            finish_reason=candidates[0].get("finishReason", ""),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        """Stream a completion using the Gemini API."""
        model_name = model or self._default_model
        url = (
            f"{_API_BASE}/models/{model_name}:streamGenerateContent"
            f"?alt=sse&key={self._api_key}"
        )

        contents = self._convert_messages(messages)
        body: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with self._client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        text = part.get("text", "")
                        if text:
                            yield LLMChunk(content=text)

        yield LLMChunk(content="", is_final=True)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    @staticmethod
    def _convert_messages(messages: list[ChatMessage]) -> list[dict]:
        """Convert ChatMessage list to Gemini contents format."""
        contents: list[dict] = []
        system_text = ""

        for msg in messages:
            if msg.role == "system":
                system_text += msg.content + "\n"
                continue

            role = "user" if msg.role == "user" else "model"
            content = msg.content
            if system_text and msg.role == "user" and not contents:
                # Prepend system prompt to first user message
                content = f"{system_text.strip()}\n\n{content}"
                system_text = ""

            contents.append({
                "role": role,
                "parts": [{"text": content}],
            })

        return contents
