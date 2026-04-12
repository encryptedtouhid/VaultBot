"""General-purpose caching layer."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class CacheEntry:
    key: str
    value: object
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class GeneralCache:
    """General-purpose TTL cache."""

    def __init__(self, max_entries: int = 1000, default_ttl: float = 300.0) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._max = max_entries
        self._default_ttl = default_ttl

    def get(self, key: str) -> object | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        if entry.is_expired:
            del self._entries[key]
            return None
        entry.hits += 1
        return entry.value

    def set(self, key: str, value: object, ttl: float | None = None) -> None:
        self._entries[key] = CacheEntry(key=key, value=value, ttl_seconds=ttl or self._default_ttl)
        self._evict()

    def delete(self, key: str) -> bool:
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def clear(self) -> None:
        self._entries.clear()

    @property
    def size(self) -> int:
        return len(self._entries)

    def _evict(self) -> None:
        while len(self._entries) > self._max:
            oldest = min(self._entries, key=lambda k: self._entries[k].created_at)
            del self._entries[oldest]
