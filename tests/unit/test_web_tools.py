"""Unit tests for web search and web fetch tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.tools.web_fetch import WebFetcher, is_url_safe
from vaultbot.tools.web_search import (
    BraveSearchProvider,
    SearchResponse,
    SearchResult,
    TavilySearchProvider,
    WebSearchEngine,
)

# ==========================================================================
# Web Search
# ==========================================================================


class TestSearchResult:
    def test_dataclass(self) -> None:
        r = SearchResult(title="Test", url="https://example.com", snippet="A test result")
        assert r.title == "Test"

    def test_search_response(self) -> None:
        resp = SearchResponse(query="test", results=[], provider="brave")
        assert resp.query == "test"
        assert resp.provider == "brave"


class TestWebSearchEngine:
    def test_register_and_list(self) -> None:
        engine = WebSearchEngine()

        class FakeSearch:
            @property
            def provider_name(self) -> str:
                return "fake"

            async def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
                return SearchResponse(query=query, results=[], provider="fake")

        engine.register_provider(FakeSearch())
        assert "fake" in engine.list_providers()

    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        engine = WebSearchEngine()

        class FakeSearch:
            @property
            def provider_name(self) -> str:
                return "fake"

            async def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
                return SearchResponse(
                    query=query,
                    results=[
                        SearchResult(title="Result 1", url="https://example.com", snippet="Snippet")
                    ],
                    provider="fake",
                )

        engine.register_provider(FakeSearch())
        resp = await engine.search("test query")
        assert len(resp.results) == 1
        assert resp.provider == "fake"
        assert engine.search_count == 1

    @pytest.mark.asyncio
    async def test_search_unknown_raises(self) -> None:
        engine = WebSearchEngine()
        with pytest.raises(ValueError, match="Unknown search provider"):
            await engine.search("test")


class TestBraveSearchProvider:
    def test_provider_name(self) -> None:
        p = BraveSearchProvider(api_key="test")
        assert p.provider_name == "brave"

    @pytest.mark.asyncio
    async def test_search_parses_response(self) -> None:
        p = BraveSearchProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Brave Result",
                        "url": "https://brave.com",
                        "description": "A result",
                    },
                ]
            }
        }
        p._client = AsyncMock()
        p._client.get = AsyncMock(return_value=mock_resp)

        resp = await p.search("test")
        assert len(resp.results) == 1
        assert resp.results[0].title == "Brave Result"


class TestTavilySearchProvider:
    def test_provider_name(self) -> None:
        p = TavilySearchProvider(api_key="test")
        assert p.provider_name == "tavily"

    @pytest.mark.asyncio
    async def test_search_parses_response(self) -> None:
        p = TavilySearchProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {"title": "Tavily Result", "url": "https://tavily.com", "content": "Content here"},
            ]
        }
        p._client = AsyncMock()
        p._client.post = AsyncMock(return_value=mock_resp)

        resp = await p.search("test")
        assert len(resp.results) == 1
        assert resp.results[0].title == "Tavily Result"


# ==========================================================================
# Web Fetch
# ==========================================================================


class TestIsUrlSafe:
    def test_safe_https_url(self) -> None:
        assert is_url_safe("https://example.com") is True

    def test_safe_http_url(self) -> None:
        assert is_url_safe("http://example.com") is True

    def test_blocked_localhost(self) -> None:
        assert is_url_safe("http://127.0.0.1") is False

    def test_blocked_private_ip(self) -> None:
        assert is_url_safe("http://192.168.1.1") is False
        assert is_url_safe("http://10.0.0.1") is False
        assert is_url_safe("http://172.16.0.1") is False

    def test_blocked_metadata(self) -> None:
        assert is_url_safe("http://169.254.169.254/latest/meta-data/") is False

    def test_blocked_metadata_hostname(self) -> None:
        assert is_url_safe("http://metadata.google.internal") is False

    def test_blocked_ftp_scheme(self) -> None:
        assert is_url_safe("ftp://example.com/file") is False

    def test_blocked_file_scheme(self) -> None:
        assert is_url_safe("file:///etc/passwd") is False

    def test_empty_url(self) -> None:
        assert is_url_safe("") is False


class TestWebFetcher:
    @pytest.mark.asyncio
    async def test_fetch_html(self) -> None:
        fetcher = WebFetcher()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.text = "<html><title>Test Page</title><body><p>Hello world</p></body></html>"
        mock_resp.content = b"<html>...</html>"

        fetcher._client = AsyncMock()
        fetcher._client.get = AsyncMock(return_value=mock_resp)

        result = await fetcher.fetch("https://example.com")
        assert result.title == "Test Page"
        assert "Hello world" in result.text
        assert result.status_code == 200
        assert fetcher.fetch_count == 1

    @pytest.mark.asyncio
    async def test_fetch_plain_text(self) -> None:
        fetcher = WebFetcher()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"content-type": "text/plain"}
        mock_resp.text = "Plain text content"
        mock_resp.content = b"Plain text content"

        fetcher._client = AsyncMock()
        fetcher._client.get = AsyncMock(return_value=mock_resp)

        result = await fetcher.fetch("https://example.com/text")
        assert result.text == "Plain text content"
        assert result.title == ""

    @pytest.mark.asyncio
    async def test_fetch_blocked_url_raises(self) -> None:
        fetcher = WebFetcher()
        with pytest.raises(ValueError, match="SSRF"):
            await fetcher.fetch("http://169.254.169.254/latest/meta-data/")

    @pytest.mark.asyncio
    async def test_fetch_strips_html(self) -> None:
        html = "<script>alert(1)</script><style>.x{}</style><p>Content</p>"
        text = WebFetcher._html_to_text(html)
        assert "alert" not in text
        assert "Content" in text
