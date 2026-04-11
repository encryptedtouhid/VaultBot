"""Web fetch tool for retrieving and parsing web page content.

Fetches URLs and converts them to readable text.  Includes SSRF
protection (blocks internal IPs and cloud metadata endpoints).
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Blocked IP ranges for SSRF protection
_BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / cloud metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

# Blocked hostnames
_BLOCKED_HOSTS = {
    "metadata.google.internal",
    "metadata.google.com",
    "169.254.169.254",
}

_MAX_CONTENT_SIZE = 1_000_000  # 1 MB


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Result from fetching a URL."""
    url: str
    title: str
    text: str
    content_type: str
    status_code: int
    size_bytes: int


def is_url_safe(url: str) -> bool:
    """Check if a URL is safe to fetch (SSRF protection)."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if hostname in _BLOCKED_HOSTS:
        return False

    if not hostname:
        return False

    # Block non-HTTP(S) schemes
    if parsed.scheme not in ("http", "https"):
        return False

    # Try to resolve as IP and check against blocked ranges
    try:
        ip = ipaddress.ip_address(hostname)
        for network in _BLOCKED_RANGES:
            if ip in network:
                return False
    except ValueError:
        pass  # Hostname, not IP — allow (DNS resolution happens at fetch time)

    return True


class WebFetcher:
    """Fetch and parse web pages with SSRF protection."""

    def __init__(
        self,
        *,
        max_size: int = _MAX_CONTENT_SIZE,
        timeout: float = 15.0,
    ) -> None:
        self._max_size = max_size
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "VaultBot/1.0 (Web Fetch)"},
        )
        self._fetch_count: int = 0

    async def fetch(self, url: str) -> FetchResult:
        """Fetch a URL and return parsed content."""
        if not is_url_safe(url):
            raise ValueError(f"URL blocked by SSRF protection: {url}")

        logger.info("web_fetch_started", url=url[:200])

        resp = await self._client.get(url)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        raw_text = resp.text[:self._max_size]

        title = ""
        text = raw_text
        if "html" in content_type:
            title = self._extract_title(raw_text)
            text = self._html_to_text(raw_text)

        self._fetch_count += 1

        return FetchResult(
            url=url,
            title=title,
            text=text[:10000],  # Cap readable text
            content_type=content_type,
            status_code=resp.status_code,
            size_bytes=len(resp.content),
        )

    @property
    def fetch_count(self) -> int:
        return self._fetch_count

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _extract_title(html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _html_to_text(html: str) -> str:
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
