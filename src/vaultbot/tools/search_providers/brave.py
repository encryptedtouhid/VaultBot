"""Brave Search provider."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.search.brave.com/res/v1/web/search"


@dataclass(frozen=True, slots=True)
class BraveSearchResult:
    """A single Brave search result."""

    title: str
    url: str
    description: str = ""


class BraveSearchProvider:
    """Brave Search API provider."""

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        )

    @property
    def provider_name(self) -> str:
        return "brave"

    async def search(self, query: str, count: int = 10) -> list[BraveSearchResult]:
        resp = await self._client.get(_API_URL, params={"q": query, "count": count})
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append(
                BraveSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                )
            )
        return results

    async def close(self) -> None:
        await self._client.aclose()
