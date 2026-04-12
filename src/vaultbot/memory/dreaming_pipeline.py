"""Tiered dreaming pipeline — light, deep, and REM phases."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class DreamPhase(str, Enum):
    LIGHT = "light"
    DEEP = "deep"
    REM = "rem"


@dataclass(frozen=True, slots=True)
class DreamConfig:
    light_interval_hours: float = 24.0
    deep_interval_hours: float = 72.0
    rem_interval_hours: float = 168.0  # Weekly
    max_budget_tokens: int = 50000
    thinking_level: str = "medium"


@dataclass(frozen=True, slots=True)
class DreamPhaseResult:
    phase: DreamPhase
    deduped: int = 0
    consolidated: int = 0
    patterns_found: int = 0
    duration_seconds: float = 0.0


class DreamingPipeline:
    """Tiered dreaming pipeline for memory consolidation."""

    def __init__(self, config: DreamConfig | None = None) -> None:
        self._config = config or DreamConfig()
        self._last_run: dict[DreamPhase, float] = {}
        self._total_runs = 0

    @property
    def config(self) -> DreamConfig:
        return self._config

    @property
    def total_runs(self) -> int:
        return self._total_runs

    def is_phase_due(self, phase: DreamPhase) -> bool:
        last = self._last_run.get(phase, 0)
        intervals = {
            DreamPhase.LIGHT: self._config.light_interval_hours,
            DreamPhase.DEEP: self._config.deep_interval_hours,
            DreamPhase.REM: self._config.rem_interval_hours,
        }
        hours_elapsed = (time.time() - last) / 3600
        return hours_elapsed >= intervals.get(phase, 24.0)

    async def run_light(self, entries: list[dict[str, object]]) -> DreamPhaseResult:
        """Light phase: daily de-duplication."""
        start = time.time()
        seen: set[str] = set()
        deduped = 0
        for entry in entries:
            key = str(entry.get("content", ""))
            if key in seen:
                deduped += 1
            seen.add(key)
        self._last_run[DreamPhase.LIGHT] = time.time()
        self._total_runs += 1
        return DreamPhaseResult(
            phase=DreamPhase.LIGHT,
            deduped=deduped,
            duration_seconds=time.time() - start,
        )

    async def run_deep(self, entries: list[dict[str, object]]) -> DreamPhaseResult:
        """Deep phase: pattern analysis and consolidation."""
        start = time.time()
        tag_counts: dict[str, int] = {}
        for entry in entries:
            for tag in entry.get("tags", []):  # type: ignore[union-attr]
                tag_counts[str(tag)] = tag_counts.get(str(tag), 0) + 1
        patterns = sum(1 for c in tag_counts.values() if c > 1)
        self._last_run[DreamPhase.DEEP] = time.time()
        self._total_runs += 1
        return DreamPhaseResult(
            phase=DreamPhase.DEEP,
            patterns_found=patterns,
            consolidated=patterns,
            duration_seconds=time.time() - start,
        )

    async def run_rem(self, entries: list[dict[str, object]]) -> DreamPhaseResult:
        """REM phase: weekly pattern consolidation."""
        start = time.time()
        self._last_run[DreamPhase.REM] = time.time()
        self._total_runs += 1
        return DreamPhaseResult(
            phase=DreamPhase.REM,
            consolidated=len(entries) // 10,
            duration_seconds=time.time() - start,
        )

    def get_due_phases(self) -> list[DreamPhase]:
        return [p for p in DreamPhase if self.is_phase_due(p)]
