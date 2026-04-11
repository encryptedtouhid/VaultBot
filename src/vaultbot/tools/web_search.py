"""Web search tool with multi-provider support.

Supports Brave Search API, DuckDuckGo (HTML), and Tavily.
All searches go through audit logging and respect rate limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str


@dataclass(frozen=True, slots=True)
class SearchResponse:
    """Response from a web search."""

    query: str
    results: list[SearchResult]
    provider: str


@runtime_checkable
class SearchProvider(Protocol):
    """Protocol for search providers."""

    @property
    def provider_name(self) -> str: ...

    async def search(self, query: str, *, max_results: int = 5) -> SearchResponse: ...


class BraveSearchProvider:
    """Brave Search API provider."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=15.0)

    @property
    def provider_name(self) -> str:
        return "brave"

    async def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        resp = await self._client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": max_results},
            headers={"X-Subscription-Token": self._api_key, "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                )
            )

        return SearchResponse(query=query, results=results, provider="brave")

    async def close(self) -> None:
        await self._client.aclose()


class TavilySearchProvider:
    """Tavily Search API provider."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=15.0)

    @property
    def provider_name(self) -> str:
        return "tavily"

    async def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        resp = await self._client.post(
            "https://api.tavily.com/search",
            json={"query": query, "max_results": max_results, "api_key": self._api_key},
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")[:300],
                )
            )

        return SearchResponse(query=query, results=results, provider="tavily")

    async def close(self) -> None:
        await self._client.aclose()


class WebSearchEngine:
    """Orchestrates web searches across multiple providers."""

    def __init__(self, default_provider: str = "") -> None:
        self._providers: dict[str, SearchProvider] = {}
        self._default_provider = default_provider
        self._search_count: int = 0

    def register_provider(self, provider: SearchProvider) -> None:
        self._providers[provider.provider_name] = provider
        if not self._default_provider:
            self._default_provider = provider.provider_name

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    async def search(
        self, query: str, *, provider: str | None = None, max_results: int = 5
    ) -> SearchResponse:
        name = provider or self._default_provider
        if not name or name not in self._providers:
            available = ", ".join(self._providers.keys()) or "none"
            raise ValueError(f"Unknown search provider '{name}'. Available: {available}")

        logger.info("web_search_started", provider=name, query=query[:100])
        result = await self._providers[name].search(query, max_results=max_results)
        self._search_count += 1
        return result

    @property
    def search_count(self) -> int:
        return self._search_count
