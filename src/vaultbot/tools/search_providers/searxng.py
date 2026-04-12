"""SearXNG meta-search provider."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SearXNGResult:
    """A SearXNG search result."""

    title: str
    url: str
    content: str = ""
    engine: str = ""


class SearXNGProvider:
    """SearXNG self-hosted meta-search provider."""

    def __init__(self, instance_url: str = "https://searx.be") -> None:
        self._client = httpx.AsyncClient(
            base_url=instance_url.rstrip("/"),
            timeout=30.0,
        )

    @property
    def provider_name(self) -> str:
        return "searxng"

    async def search(self, query: str, categories: str = "general") -> list[SearXNGResult]:
        resp = await self._client.get(
            "/search",
            params={"q": query, "format": "json", "categories": categories},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearXNGResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                engine=r.get("engine", ""),
            )
            for r in data.get("results", [])
        ]

    async def close(self) -> None:
        await self._client.aclose()
