"""ACP session with TTL-based eviction and identity reconciliation."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ACPSessionState(str, Enum):
    """ACP session lifecycle state."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EVICTED = "evicted"
    CLOSED = "closed"


class IdentityState(str, Enum):
    """Session identity reconciliation state."""

    STABLE = "stable"
    UNSTABLE = "unstable"
    PENDING = "pending"


@dataclass(slots=True)
class SessionIdentity:
    """Identity information bound to an ACP session."""

    user_id: str = ""
    platform: str = ""
    display_name: str = ""
    state: IdentityState = IdentityState.PENDING
    reconciled_at: float = 0.0


@dataclass(slots=True)
class ACPSession:
    """An ACP-managed session with lifecycle tracking."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    identity: SessionIdentity = field(default_factory=SessionIdentity)
    state: ACPSessionState = ACPSessionState.PENDING
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    idle_ttl_seconds: float = 86400.0  # 24h default
    turn_count: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > self.idle_ttl_seconds

    def touch(self) -> None:
        self.last_activity = time.time()
        self.turn_count += 1


class ACPSessionStore:
    """In-memory ACP session store with eviction."""

    def __init__(self, max_sessions: int = 5000) -> None:
        self._sessions: dict[str, ACPSession] = {}
        self._max_sessions = max_sessions

    @property
    def count(self) -> int:
        return len(self._sessions)

    def create(self, identity: SessionIdentity | None = None) -> ACPSession:
        session = ACPSession(identity=identity or SessionIdentity())
        session.state = ACPSessionState.ACTIVE
        self._sessions[session.session_id] = session
        self._evict_if_over_limit()
        logger.info("acp_session_created", session_id=session.session_id)
        return session

    def get(self, session_id: str) -> ACPSession | None:
        session = self._sessions.get(session_id)
        if session and session.state == ACPSessionState.EVICTED:
            return None
        return session

    def close(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.state = ACPSessionState.CLOSED
        del self._sessions[session_id]
        return True

    def suspend(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session or session.state != ACPSessionState.ACTIVE:
            return False
        session.state = ACPSessionState.SUSPENDED
        return True

    def resume(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session or session.state != ACPSessionState.SUSPENDED:
            return False
        session.state = ACPSessionState.ACTIVE
        session.touch()
        return True

    def reconcile_identity(self, session_id: str, user_id: str, platform: str = "") -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.identity.user_id = user_id
        session.identity.platform = platform
        session.identity.state = IdentityState.STABLE
        session.identity.reconciled_at = time.time()
        return True

    def evict_expired(self) -> int:
        """Evict sessions past their idle TTL. Returns count evicted."""
        to_evict = [
            sid
            for sid, s in self._sessions.items()
            if s.is_expired and s.state == ACPSessionState.ACTIVE
        ]
        for sid in to_evict:
            self._sessions[sid].state = ACPSessionState.EVICTED
            del self._sessions[sid]
        if to_evict:
            logger.info("acp_sessions_evicted", count=len(to_evict))
        return len(to_evict)

    def _evict_if_over_limit(self) -> None:
        while len(self._sessions) > self._max_sessions:
            oldest = min(self._sessions, key=lambda k: self._sessions[k].last_activity)
            self._sessions[oldest].state = ACPSessionState.EVICTED
            del self._sessions[oldest]
