"""Link extraction with SSRF validation and dedup."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

_URL_PATTERN = re.compile(r"https?://[^\s\)<>\]\"]+")
_BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "[::1]"})
_BLOCKED_PREFIXES = ("10.", "172.16.", "172.17.", "192.168.")


@dataclass(frozen=True, slots=True)
class ExtractedLink:
    url: str
    safe: bool = True
    reason: str = ""


def is_safe_url(url: str) -> tuple[bool, str]:
    """Check URL safety. Returns (is_safe, reason)."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.scheme not in ("http", "https"):
            return False, f"blocked scheme: {parsed.scheme}"
        if host in _BLOCKED_HOSTS:
            return False, f"blocked host: {host}"
        if any(host.startswith(p) for p in _BLOCKED_PREFIXES):
            return False, f"private IP: {host}"
        return True, ""
    except Exception:
        return False, "invalid URL"


def extract_links(text: str, max_links: int = 20, deduplicate: bool = True) -> list[ExtractedLink]:
    """Extract HTTP/HTTPS links from text with safety checking."""
    urls = _URL_PATTERN.findall(text)
    seen: set[str] = set()
    results: list[ExtractedLink] = []

    for url in urls:
        url = url.rstrip(".,;:!?)")
        if deduplicate and url in seen:
            continue
        seen.add(url)
        safe, reason = is_safe_url(url)
        results.append(ExtractedLink(url=url, safe=safe, reason=reason))
        if len(results) >= max_links:
            break

    return results
