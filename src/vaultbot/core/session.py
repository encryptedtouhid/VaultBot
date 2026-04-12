"""Session management with lifecycle and multi-agent support."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class SessionState(str, Enum):
    """Session lifecycle state."""

    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    CLOSED = "closed"


@dataclass(slots=True)
class Session:
    """A user session."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    user_id: str = ""
    platform: str = ""
    state: SessionState = SessionState.ACTIVE
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    metadata: dict[str, str] = field(default_factory=dict)
    agent_ids: list[str] = field(default_factory=list)


class SessionManager:
    """Manages user sessions across platforms."""

    def __init__(self, idle_timeout: float = 1800.0, max_sessions: int = 10000) -> None:
        self._sessions: dict[str, Session] = {}
        self._user_sessions: dict[str, list[str]] = {}
        self._idle_timeout = idle_timeout
        self._max_sessions = max_sessions

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    def create_session(self, user_id: str, platform: str = "") -> Session:
        session = Session(user_id=user_id, platform=platform)
        self._sessions[session.session_id] = session
        self._user_sessions.setdefault(user_id, []).append(session.session_id)
        logger.info("session_created", session_id=session.session_id, user_id=user_id)
        return session

    def get_session(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = time.time()
        return session

    def get_user_sessions(self, user_id: str) -> list[Session]:
        ids = self._user_sessions.get(user_id, [])
        return [self._sessions[sid] for sid in ids if sid in self._sessions]

    def close_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.state = SessionState.CLOSED
        del self._sessions[session_id]
        user_ids = self._user_sessions.get(session.user_id, [])
        if session_id in user_ids:
            user_ids.remove(session_id)
        logger.info("session_closed", session_id=session_id)
        return True

    def add_agent_to_session(self, session_id: str, agent_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        if agent_id not in session.agent_ids:
            session.agent_ids.append(agent_id)
        return True

    def cleanup_idle(self) -> int:
        """Close idle sessions. Returns count closed."""
        now = time.time()
        to_close = [
            sid
            for sid, s in self._sessions.items()
            if s.state == SessionState.ACTIVE and (now - s.last_activity) > self._idle_timeout
        ]
        for sid in to_close:
            self.close_session(sid)
        return len(to_close)
