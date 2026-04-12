"""Perplexity search provider."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

_API_URL = "https://api.perplexity.ai/chat/completions"


@dataclass(frozen=True, slots=True)
class PerplexityResult:
    """A Perplexity search result."""

    answer: str
    citations: list[str]


class PerplexityProvider:
    """Perplexity AI search provider using the Sonar API."""

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def provider_name(self) -> str:
        return "perplexity"

    async def search(self, query: str) -> PerplexityResult:
        resp = await self._client.post(
            _API_URL,
            json={
                "model": "llama-3.1-sonar-large-128k-online",
                "messages": [{"role": "user", "content": query}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        answer = choices[0]["message"]["content"] if choices else ""
        citations = data.get("citations", [])
        return PerplexityResult(answer=answer, citations=citations)

    async def close(self) -> None:
        await self._client.aclose()
