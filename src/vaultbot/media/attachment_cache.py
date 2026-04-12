"""Attachment caching for media understanding."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class CachedAttachment:
    key: str
    data: bytes
    mime_type: str = ""
    cached_at: float = field(default_factory=time.time)
    access_count: int = 0


class AttachmentCache:
    """Cache for media attachments to avoid re-downloading."""

    def __init__(self, max_entries: int = 100, ttl_seconds: float = 3600.0) -> None:
        self._cache: dict[str, CachedAttachment] = {}
        self._max_entries = max_entries
        self._ttl = ttl_seconds

    @staticmethod
    def _make_key(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def get(self, url: str) -> CachedAttachment | None:
        key = self._make_key(url)
        entry = self._cache.get(key)
        if not entry:
            return None
        if (time.time() - entry.cached_at) > self._ttl:
            del self._cache[key]
            return None
        entry.access_count += 1
        return entry

    def put(self, url: str, data: bytes, mime_type: str = "") -> CachedAttachment:
        key = self._make_key(url)
        entry = CachedAttachment(key=key, data=data, mime_type=mime_type)
        self._cache[key] = entry
        self._evict()
        return entry

    def invalidate(self, url: str) -> bool:
        key = self._make_key(url)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)

    def _evict(self) -> None:
        while len(self._cache) > self._max_entries:
            oldest = min(self._cache, key=lambda k: self._cache[k].cached_at)
            del self._cache[oldest]
