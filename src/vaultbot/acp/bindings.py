"""ACP persistent session-actor bindings for routing."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Binding:
    """A session-actor binding."""

    session_id: str
    actor_id: str
    created_at: float = field(default_factory=time.time)
    priority: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


class BindingRegistry:
    """Manages persistent session-actor bindings."""

    def __init__(self) -> None:
        self._bindings: dict[str, list[Binding]] = {}

    def bind(self, session_id: str, actor_id: str, priority: int = 0) -> Binding:
        binding = Binding(session_id=session_id, actor_id=actor_id, priority=priority)
        self._bindings.setdefault(session_id, []).append(binding)
        return binding

    def unbind(self, session_id: str, actor_id: str) -> bool:
        bindings = self._bindings.get(session_id, [])
        before = len(bindings)
        self._bindings[session_id] = [b for b in bindings if b.actor_id != actor_id]
        return len(self._bindings[session_id]) < before

    def resolve(self, session_id: str) -> str | None:
        """Resolve the highest-priority actor for a session."""
        bindings = self._bindings.get(session_id, [])
        if not bindings:
            return None
        return max(bindings, key=lambda b: b.priority).actor_id

    def get_bindings(self, session_id: str) -> list[Binding]:
        return list(self._bindings.get(session_id, []))

    def clear_session(self, session_id: str) -> None:
        self._bindings.pop(session_id, None)

    @property
    def total_bindings(self) -> int:
        return sum(len(v) for v in self._bindings.values())
