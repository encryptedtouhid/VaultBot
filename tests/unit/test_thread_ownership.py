"""Unit tests for thread ownership."""

from __future__ import annotations

from vaultbot.core.thread import ThreadManager, ThreadState


class TestThreadManager:
    def test_create_thread(self) -> None:
        mgr = ThreadManager()
        t = mgr.create_thread("user1", "telegram", "chat1")
        assert t.owner_id == "user1"
        assert "user1" in t.participants
        assert mgr.thread_count == 1

    def test_get_thread(self) -> None:
        mgr = ThreadManager()
        t = mgr.create_thread("user1")
        assert mgr.get_thread(t.thread_id) is not None
        assert mgr.get_thread("nope") is None

    def test_is_owner(self) -> None:
        mgr = ThreadManager()
        t = mgr.create_thread("user1")
        assert mgr.is_owner(t.thread_id, "user1") is True
        assert mgr.is_owner(t.thread_id, "user2") is False

    def test_add_participant(self) -> None:
        mgr = ThreadManager()
        t = mgr.create_thread("user1")
        assert mgr.add_participant(t.thread_id, "user2") is True
        assert "user2" in mgr.get_thread(t.thread_id).participants

    def test_archive_thread(self) -> None:
        mgr = ThreadManager()
        t = mgr.create_thread("user1")
        assert mgr.archive_thread(t.thread_id) is True
        assert mgr.get_thread(t.thread_id).state == ThreadState.ARCHIVED

    def test_delete_thread(self) -> None:
        mgr = ThreadManager()
        t = mgr.create_thread("user1")
        assert mgr.delete_thread(t.thread_id) is True
        assert mgr.thread_count == 0

    def test_list_user_threads(self) -> None:
        mgr = ThreadManager()
        mgr.create_thread("user1")
        mgr.create_thread("user1")
        mgr.create_thread("user2")
        assert len(mgr.list_user_threads("user1")) == 2

    def test_archive_idle(self) -> None:
        mgr = ThreadManager(idle_timeout=0)
        t = mgr.create_thread("user1")
        t.last_activity = 0
        count = mgr.archive_idle()
        assert count == 1
        assert mgr.get_thread(t.thread_id).state == ThreadState.IDLE
