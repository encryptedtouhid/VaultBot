"""Runtime diagnostic event capture."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DiagnosticSnapshot:
    timestamp: float = field(default_factory=time.time)
    python_version: str = ""
    platform: str = ""
    memory_mb: float = 0.0
    active_sessions: int = 0
    active_agents: int = 0
    uptime_seconds: float = 0.0
    errors_last_hour: int = 0


class DiagnosticCollector:
    """Collects runtime diagnostic snapshots."""

    def __init__(self) -> None:
        self._start_time = time.time()
        self._error_count = 0
        self._snapshots: list[DiagnosticSnapshot] = []

    def record_error(self) -> None:
        self._error_count += 1

    def capture(self, active_sessions: int = 0, active_agents: int = 0) -> DiagnosticSnapshot:
        snapshot = DiagnosticSnapshot(
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            platform=sys.platform,
            active_sessions=active_sessions,
            active_agents=active_agents,
            uptime_seconds=time.time() - self._start_time,
            errors_last_hour=self._error_count,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_recent(self, limit: int = 10) -> list[DiagnosticSnapshot]:
        return self._snapshots[-limit:]

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)
