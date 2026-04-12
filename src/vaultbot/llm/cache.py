"""Prompt caching for cost optimization."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class CacheEntry:
    key: str
    response: str
    model: str = ""
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 3600.0
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


@dataclass(frozen=True, slots=True)
class CacheStats:
    total_entries: int = 0
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0


class PromptCache:
    """In-memory prompt cache with TTL-based expiry."""

    def __init__(self, max_entries: int = 1000, default_ttl: float = 3600.0) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(prompt: str, model: str = "", temperature: float = 0.7) -> str:
        raw = f"{model}:{temperature}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, prompt: str, model: str = "", temperature: float = 0.7) -> str | None:
        key = self._make_key(prompt, model, temperature)
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            entry.hit_count += 1
            self._hits += 1
            logger.debug("cache_hit", key=key[:8])
            return entry.response
        if entry and entry.is_expired:
            del self._cache[key]
        self._misses += 1
        return None

    def put(
        self,
        prompt: str,
        response: str,
        model: str = "",
        temperature: float = 0.7,
        ttl: float | None = None,
    ) -> None:
        key = self._make_key(prompt, model, temperature)
        self._cache[key] = CacheEntry(
            key=key,
            response=response,
            model=model,
            ttl_seconds=ttl or self._default_ttl,
        )
        self._evict_if_needed()

    def invalidate(self, prompt: str, model: str = "", temperature: float = 0.7) -> bool:
        key = self._make_key(prompt, model, temperature)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> CacheStats:
        total = self._hits + self._misses
        return CacheStats(
            total_entries=len(self._cache),
            hits=self._hits,
            misses=self._misses,
            hit_rate=self._hits / total if total > 0 else 0.0,
        )

    def _evict_if_needed(self) -> None:
        while len(self._cache) > self._max_entries:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]
