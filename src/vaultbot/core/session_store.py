"""Session storage backend."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vaultbot.core.session import Session
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class SessionStore(Protocol):
    """Protocol for session storage backends."""

    async def save(self, session: Session) -> None: ...
    async def load(self, session_id: str) -> Session | None: ...
    async def delete(self, session_id: str) -> bool: ...
    async def list_sessions(self, user_id: str) -> list[Session]: ...


class InMemorySessionStore:
    """In-memory session store for development/testing."""

    def __init__(self) -> None:
        self._store: dict[str, Session] = {}

    async def save(self, session: Session) -> None:
        self._store[session.session_id] = session

    async def load(self, session_id: str) -> Session | None:
        return self._store.get(session_id)

    async def delete(self, session_id: str) -> bool:
        if session_id in self._store:
            del self._store[session_id]
            return True
        return False

    async def list_sessions(self, user_id: str) -> list[Session]:
        return [s for s in self._store.values() if s.user_id == user_id]
