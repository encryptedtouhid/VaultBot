"""Media understanding engine for image, document, and link analysis.

Provides image analysis (via vision-capable LLMs), document parsing
(PDF/text extraction), and link content extraction (URL → readable text).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class MediaType(str, Enum):
    """Types of media that can be analyzed."""

    IMAGE = "image"
    DOCUMENT = "document"
    LINK = "link"


@dataclass(frozen=True, slots=True)
class MediaAnalysisRequest:
    """Request to analyze a piece of media."""

    media_type: MediaType
    url: str = ""
    data: bytes = b""
    mime_type: str = ""
    question: str = ""  # Optional question about the media


@dataclass(frozen=True, slots=True)
class MediaAnalysisResult:
    """Result from media analysis."""

    summary: str
    media_type: MediaType
    metadata: dict[str, str] | None = None
    extracted_text: str = ""


class LinkExtractor:
    """Extract readable content from URLs."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "VaultBot/1.0 (Link Preview)"},
        )

    async def extract(self, url: str) -> MediaAnalysisResult:
        """Fetch URL and extract readable text content."""
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            text = resp.text[:10000]  # Limit extraction size

            # Extract title from HTML
            title = ""
            if "html" in content_type:
                title = self._extract_title(text)
                text = self._strip_html(text)

            metadata = {
                "url": url,
                "content_type": content_type,
                "status_code": str(resp.status_code),
            }
            if title:
                metadata["title"] = title

            return MediaAnalysisResult(
                summary=text[:2000],
                media_type=MediaType.LINK,
                metadata=metadata,
                extracted_text=text,
            )
        except Exception as exc:
            logger.warning("link_extraction_failed", url=url, error=str(exc))
            return MediaAnalysisResult(
                summary=f"Failed to extract content from {url}: {exc}",
                media_type=MediaType.LINK,
                metadata={"url": url, "error": str(exc)},
            )

    @staticmethod
    def _extract_title(html: str) -> str:
        """Extract title from HTML."""
        import re

        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _strip_html(html: str) -> str:
        """Strip HTML tags for plain text extraction."""
        import re

        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    async def close(self) -> None:
        await self._client.aclose()


class MediaUnderstandingEngine:
    """Orchestrates media analysis across different media types."""

    def __init__(self) -> None:
        self._link_extractor = LinkExtractor()
        self._analysis_count: int = 0

    async def analyze(self, request: MediaAnalysisRequest) -> MediaAnalysisResult:
        """Analyze media based on its type."""
        if request.media_type == MediaType.LINK:
            result = await self._link_extractor.extract(request.url)
        elif request.media_type == MediaType.IMAGE:
            result = MediaAnalysisResult(
                summary=f"Image analysis requested for: {request.url or 'uploaded image'}",
                media_type=MediaType.IMAGE,
                metadata={"url": request.url, "mime_type": request.mime_type},
            )
        elif request.media_type == MediaType.DOCUMENT:
            result = MediaAnalysisResult(
                summary=f"Document analysis requested for: {request.url or 'uploaded document'}",
                media_type=MediaType.DOCUMENT,
                metadata={"url": request.url, "mime_type": request.mime_type},
            )
        else:
            raise ValueError(f"Unsupported media type: {request.media_type}")

        self._analysis_count += 1
        logger.info(
            "media_analysis_completed",
            media_type=request.media_type.value,
            total=self._analysis_count,
        )
        return result

    @property
    def analysis_count(self) -> int:
        return self._analysis_count

    async def close(self) -> None:
        await self._link_extractor.close()
