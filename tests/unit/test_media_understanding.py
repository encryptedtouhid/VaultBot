"""Unit tests for media understanding engine."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.media.understanding import (
    LinkExtractor,
    MediaAnalysisRequest,
    MediaType,
    MediaUnderstandingEngine,
)


class TestMediaTypes:
    def test_media_type_enum(self) -> None:
        assert MediaType.IMAGE.value == "image"
        assert MediaType.LINK.value == "link"
        assert MediaType.DOCUMENT.value == "document"

    def test_request_defaults(self) -> None:
        req = MediaAnalysisRequest(media_type=MediaType.LINK, url="https://example.com")
        assert req.data == b""
        assert req.question == ""


class TestLinkExtractor:
    def test_extract_title(self) -> None:
        html = "<html><head><title>My Page</title></head><body>content</body></html>"
        assert LinkExtractor._extract_title(html) == "My Page"

    def test_extract_title_missing(self) -> None:
        assert LinkExtractor._extract_title("<html><body>no title</body></html>") == ""

    def test_strip_html(self) -> None:
        html = "<p>Hello <b>World</b></p><script>evil()</script>"
        result = LinkExtractor._strip_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "script" not in result
        assert "evil" not in result

    def test_strip_html_style(self) -> None:
        html = "<style>.foo{color:red}</style><p>text</p>"
        result = LinkExtractor._strip_html(html)
        assert "color" not in result
        assert "text" in result

    @pytest.mark.asyncio
    async def test_extract_success(self) -> None:
        extractor = LinkExtractor()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.text = (
            "<html><head><title>Test</title></head><body><p>Hello world</p></body></html>"
        )

        extractor._client = AsyncMock()
        extractor._client.get = AsyncMock(return_value=mock_resp)

        result = await extractor.extract("https://example.com")
        assert result.media_type == MediaType.LINK
        assert "Hello world" in result.summary
        assert result.metadata is not None
        assert result.metadata["title"] == "Test"

    @pytest.mark.asyncio
    async def test_extract_failure_handled(self) -> None:
        extractor = LinkExtractor()
        extractor._client = AsyncMock()
        extractor._client.get = AsyncMock(side_effect=Exception("timeout"))

        result = await extractor.extract("https://bad.example.com")
        assert "Failed" in result.summary
        assert result.metadata is not None
        assert "error" in result.metadata


class TestMediaUnderstandingEngine:
    @pytest.mark.asyncio
    async def test_analyze_link(self) -> None:
        engine = MediaUnderstandingEngine()
        engine._link_extractor._client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"content-type": "text/plain"}
        mock_resp.text = "Plain text content from the page"
        engine._link_extractor._client.get = AsyncMock(return_value=mock_resp)

        req = MediaAnalysisRequest(media_type=MediaType.LINK, url="https://example.com")
        result = await engine.analyze(req)
        assert result.media_type == MediaType.LINK
        assert "Plain text content" in result.summary
        assert engine.analysis_count == 1

    @pytest.mark.asyncio
    async def test_analyze_image(self) -> None:
        engine = MediaUnderstandingEngine()
        req = MediaAnalysisRequest(media_type=MediaType.IMAGE, url="https://example.com/photo.jpg")
        result = await engine.analyze(req)
        assert result.media_type == MediaType.IMAGE
        assert engine.analysis_count == 1

    @pytest.mark.asyncio
    async def test_analyze_document(self) -> None:
        engine = MediaUnderstandingEngine()
        req = MediaAnalysisRequest(
            media_type=MediaType.DOCUMENT, url="report.pdf", mime_type="application/pdf"
        )
        result = await engine.analyze(req)
        assert result.media_type == MediaType.DOCUMENT
        assert "document" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_analysis_count(self) -> None:
        engine = MediaUnderstandingEngine()
        for _ in range(3):
            await engine.analyze(MediaAnalysisRequest(media_type=MediaType.IMAGE, url="img.png"))
        assert engine.analysis_count == 3
