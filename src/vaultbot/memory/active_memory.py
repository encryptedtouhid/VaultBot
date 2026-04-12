"""Active memory that surfaces relevant context proactively."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class MemoryEntry:
    """An active memory entry."""

    key: str
    content: str
    relevance_score: float = 0.0
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)


class ActiveMemoryStore:
    """Active memory that surfaces relevant context based on recency and frequency."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._entries: dict[str, MemoryEntry] = {}
        self._max_entries = max_entries

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def store(self, key: str, content: str, tags: list[str] | None = None) -> MemoryEntry:
        entry = MemoryEntry(key=key, content=content, tags=tags or [])
        self._entries[key] = entry
        self._evict_if_needed()
        return entry

    def recall(self, key: str) -> MemoryEntry | None:
        entry = self._entries.get(key)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
        return entry

    def search_by_relevance(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search entries by keyword relevance."""
        query_lower = query.lower()
        scored = []
        for entry in self._entries.values():
            score = 0.0
            if query_lower in entry.content.lower():
                score += 1.0
            if query_lower in entry.key.lower():
                score += 0.5
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 0.3
            score += entry.access_count * 0.1
            if score > 0:
                entry.relevance_score = score
                scored.append(entry)
        scored.sort(key=lambda e: e.relevance_score, reverse=True)
        return scored[:limit]

    def forget(self, key: str) -> bool:
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def _evict_if_needed(self) -> None:
        while len(self._entries) > self._max_entries:
            oldest_key = min(self._entries, key=lambda k: self._entries[k].last_accessed)
            del self._entries[oldest_key]
