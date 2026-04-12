"""Tavily AI search provider."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

_API_URL = "https://api.tavily.com/search"


@dataclass(frozen=True, slots=True)
class TavilyResult:
    """A Tavily search result."""

    title: str
    url: str
    content: str = ""
    score: float = 0.0


class TavilyProvider:
    """Tavily AI-powered search provider."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def provider_name(self) -> str:
        return "tavily"

    async def search(self, query: str, max_results: int = 5) -> list[TavilyResult]:
        resp = await self._client.post(
            _API_URL,
            json={"api_key": self._api_key, "query": query, "max_results": max_results},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            TavilyResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0),
            )
            for r in data.get("results", [])
        ]

    async def close(self) -> None:
        await self._client.aclose()
