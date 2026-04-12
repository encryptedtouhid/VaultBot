"""ACP provenance tracking for audit trails."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ProvenanceMode(str, Enum):
    OFF = "off"
    META = "meta"
    META_RECEIPT = "meta_receipt"


@dataclass(frozen=True, slots=True)
class ProvenanceEntry:
    session_id: str
    action: str
    actor: str = ""
    timestamp: float = field(default_factory=time.time)
    turn_latency_ms: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


class ProvenanceTracker:
    """Tracks provenance/audit trail for ACP sessions."""

    def __init__(self, mode: ProvenanceMode = ProvenanceMode.META) -> None:
        self._mode = mode
        self._entries: list[ProvenanceEntry] = []

    @property
    def mode(self) -> ProvenanceMode:
        return self._mode

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def record(
        self,
        session_id: str,
        action: str,
        actor: str = "",
        turn_latency_ms: int = 0,
        metadata: dict[str, str] | None = None,
    ) -> ProvenanceEntry | None:
        if self._mode == ProvenanceMode.OFF:
            return None
        entry = ProvenanceEntry(
            session_id=session_id,
            action=action,
            actor=actor,
            turn_latency_ms=turn_latency_ms,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        return entry

    def get_session_trail(self, session_id: str) -> list[ProvenanceEntry]:
        return [e for e in self._entries if e.session_id == session_id]

    def get_recent(self, limit: int = 50) -> list[ProvenanceEntry]:
        return self._entries[-limit:]

    def clear_session(self, session_id: str) -> int:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.session_id != session_id]
        return before - len(self._entries)
