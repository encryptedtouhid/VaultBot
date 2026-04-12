"""Unit tests for search providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _mock_client(json_data: dict) -> AsyncMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=json_data)
    client = AsyncMock()
    client.get = AsyncMock(return_value=mock_resp)
    client.post = AsyncMock(return_value=mock_resp)
    return client


class TestBraveSearch:
    def test_provider_name(self) -> None:
        from vaultbot.tools.search_providers.brave import BraveSearchProvider

        assert BraveSearchProvider(api_key="k").provider_name == "brave"

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        from vaultbot.tools.search_providers.brave import BraveSearchProvider

        p = BraveSearchProvider(api_key="k")
        p._client = _mock_client(
            {"web": {"results": [{"title": "Test", "url": "http://t.com", "description": "d"}]}}
        )
        results = await p.search("test")
        assert len(results) == 1
        assert results[0].title == "Test"


class TestSearXNG:
    def test_provider_name(self) -> None:
        from vaultbot.tools.search_providers.searxng import SearXNGProvider

        assert SearXNGProvider().provider_name == "searxng"

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        from vaultbot.tools.search_providers.searxng import SearXNGProvider

        p = SearXNGProvider()
        p._client = _mock_client(
            {"results": [{"title": "Test", "url": "http://t.com", "content": "c", "engine": "g"}]}
        )
        results = await p.search("test")
        assert len(results) == 1


class TestTavily:
    def test_provider_name(self) -> None:
        from vaultbot.tools.search_providers.tavily import TavilyProvider

        assert TavilyProvider(api_key="k").provider_name == "tavily"

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        from vaultbot.tools.search_providers.tavily import TavilyProvider

        p = TavilyProvider(api_key="k")
        p._client = _mock_client(
            {"results": [{"title": "T", "url": "http://t.com", "content": "c", "score": 0.9}]}
        )
        results = await p.search("test")
        assert len(results) == 1
        assert results[0].score == 0.9


class TestPerplexity:
    def test_provider_name(self) -> None:
        from vaultbot.tools.search_providers.perplexity import PerplexityProvider

        assert PerplexityProvider(api_key="k").provider_name == "perplexity"

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        from vaultbot.tools.search_providers.perplexity import PerplexityProvider

        p = PerplexityProvider(api_key="k")
        p._client = _mock_client(
            {
                "choices": [{"message": {"content": "answer"}}],
                "citations": ["http://c.com"],
            }
        )
        result = await p.search("test")
        assert result.answer == "answer"
        assert len(result.citations) == 1
