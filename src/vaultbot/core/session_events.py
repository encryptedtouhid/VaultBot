"""Observable session lifecycle events."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class SessionEventType(str, Enum):
    CREATED = "created"
    DELETED = "deleted"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    MESSAGE = "message"
    MODEL_OVERRIDE = "model_override"


@dataclass(frozen=True, slots=True)
class SessionEvent:
    event_type: SessionEventType
    session_id: str
    parent_id: str = ""
    label: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


SessionEventCallback = Callable[[SessionEvent], None]


class SessionEventEmitter:
    """Emits and listens for session lifecycle events."""

    def __init__(self) -> None:
        self._listeners: dict[SessionEventType, list[SessionEventCallback]] = {}
        self._event_log: list[SessionEvent] = []

    def on(self, event_type: SessionEventType, callback: SessionEventCallback) -> None:
        self._listeners.setdefault(event_type, []).append(callback)

    def off(self, event_type: SessionEventType, callback: SessionEventCallback) -> bool:
        listeners = self._listeners.get(event_type, [])
        if callback in listeners:
            listeners.remove(callback)
            return True
        return False

    def emit(self, event: SessionEvent) -> int:
        self._event_log.append(event)
        callbacks = self._listeners.get(event.event_type, [])
        for cb in callbacks:
            cb(event)
        return len(callbacks)

    def get_log(self, session_id: str = "", limit: int = 50) -> list[SessionEvent]:
        events = self._event_log
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        return events[-limit:]

    @property
    def total_events(self) -> int:
        return len(self._event_log)
