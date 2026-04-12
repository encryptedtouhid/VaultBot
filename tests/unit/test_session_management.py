"""Unit tests for session management."""

from __future__ import annotations

import pytest

from vaultbot.core.session import Session, SessionManager, SessionState
from vaultbot.core.session_store import InMemorySessionStore, SessionStore


class TestSession:
    def test_defaults(self) -> None:
        s = Session(user_id="u1")
        assert s.state == SessionState.ACTIVE
        assert s.agent_ids == []


class TestSessionManager:
    def test_create_session(self) -> None:
        mgr = SessionManager()
        s = mgr.create_session("user1", "telegram")
        assert s.user_id == "user1"
        assert mgr.session_count == 1

    def test_get_session(self) -> None:
        mgr = SessionManager()
        s = mgr.create_session("user1")
        assert mgr.get_session(s.session_id) is not None
        assert mgr.get_session("missing") is None

    def test_get_user_sessions(self) -> None:
        mgr = SessionManager()
        mgr.create_session("user1")
        mgr.create_session("user1")
        assert len(mgr.get_user_sessions("user1")) == 2

    def test_close_session(self) -> None:
        mgr = SessionManager()
        s = mgr.create_session("user1")
        assert mgr.close_session(s.session_id) is True
        assert mgr.session_count == 0

    def test_close_unknown(self) -> None:
        mgr = SessionManager()
        assert mgr.close_session("nope") is False

    def test_add_agent(self) -> None:
        mgr = SessionManager()
        s = mgr.create_session("user1")
        assert mgr.add_agent_to_session(s.session_id, "agent1") is True
        assert "agent1" in mgr.get_session(s.session_id).agent_ids

    def test_cleanup_idle(self) -> None:
        mgr = SessionManager(idle_timeout=0)
        s = mgr.create_session("user1")
        s.last_activity = 0
        closed = mgr.cleanup_idle()
        assert closed == 1


class TestInMemorySessionStore:
    def test_is_session_store(self) -> None:
        assert isinstance(InMemorySessionStore(), SessionStore)

    @pytest.mark.asyncio
    async def test_save_and_load(self) -> None:
        store = InMemorySessionStore()
        s = Session(user_id="u1")
        await store.save(s)
        loaded = await store.load(s.session_id)
        assert loaded is not None
        assert loaded.user_id == "u1"

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        store = InMemorySessionStore()
        s = Session(user_id="u1")
        await store.save(s)
        assert await store.delete(s.session_id) is True
        assert await store.load(s.session_id) is None

    @pytest.mark.asyncio
    async def test_list_sessions(self) -> None:
        store = InMemorySessionStore()
        await store.save(Session(user_id="u1"))
        await store.save(Session(user_id="u1"))
        await store.save(Session(user_id="u2"))
        assert len(await store.list_sessions("u1")) == 2
