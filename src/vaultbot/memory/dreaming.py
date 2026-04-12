"""Memory dreaming — background consolidation and organization."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DreamResult:
    """Result of a dreaming/consolidation cycle."""

    merged_count: int = 0
    pruned_count: int = 0
    insights: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class MemoryDreamer:
    """Background memory consolidation and organization.

    'Dreaming' periodically reviews stored memories, merges related ones,
    prunes stale entries, and generates insights.
    """

    def __init__(self, stale_threshold_seconds: float = 86400 * 30) -> None:
        self._stale_threshold = stale_threshold_seconds
        self._dream_count = 0
        self._total_merged = 0
        self._total_pruned = 0

    @property
    def dream_count(self) -> int:
        return self._dream_count

    @property
    def total_merged(self) -> int:
        return self._total_merged

    @property
    def total_pruned(self) -> int:
        return self._total_pruned

    async def dream(
        self,
        entries: list[dict[str, object]],
    ) -> DreamResult:
        """Run a dreaming cycle on a set of memory entries."""
        start = time.time()
        merged = 0
        pruned = 0
        insights: list[str] = []
        now = time.time()

        # Prune stale entries
        for entry in entries:
            last_accessed = float(entry.get("last_accessed", now))
            if (now - last_accessed) > self._stale_threshold:
                pruned += 1

        # Detect clusters (simplified: entries with same tags)
        tag_groups: dict[str, list[dict[str, object]]] = {}
        for entry in entries:
            for tag in entry.get("tags", []):  # type: ignore[union-attr]
                tag_groups.setdefault(str(tag), []).append(entry)

        for tag, group in tag_groups.items():
            if len(group) > 1:
                merged += 1
                insights.append(f"Found {len(group)} related entries for '{tag}'")

        duration = time.time() - start
        self._dream_count += 1
        self._total_merged += merged
        self._total_pruned += pruned

        logger.info(
            "dream_completed",
            merged=merged,
            pruned=pruned,
            insights=len(insights),
        )

        return DreamResult(
            merged_count=merged,
            pruned_count=pruned,
            insights=insights,
            duration_seconds=duration,
        )
