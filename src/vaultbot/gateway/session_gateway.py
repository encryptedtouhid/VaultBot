"""Gateway-level session management with subscriptions."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class GatewaySession:
    session_id: str
    agent_id: str = ""
    created_at: float = field(default_factory=time.time)
    last_message_at: float = 0.0
    message_count: int = 0
    subscribers: set[str] = field(default_factory=set)
    label: str = ""


class SessionGateway:
    """Gateway-level session management with subscriptions."""

    def __init__(self) -> None:
        self._sessions: dict[str, GatewaySession] = {}

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    def create(self, session_id: str, agent_id: str = "") -> GatewaySession:
        session = GatewaySession(session_id=session_id, agent_id=agent_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> GatewaySession | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def subscribe(self, session_id: str, client_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.subscribers.add(client_id)
        return True

    def unsubscribe(self, session_id: str, client_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.subscribers.discard(client_id)
        return True

    def get_subscribers(self, session_id: str) -> set[str]:
        session = self._sessions.get(session_id)
        return set(session.subscribers) if session else set()

    def record_message(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.message_count += 1
            session.last_message_at = time.time()

    def list_sessions(self, agent_id: str = "") -> list[GatewaySession]:
        sessions = list(self._sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        return sessions
