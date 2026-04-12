"""Unit tests for infrastructure utilities."""

from __future__ import annotations

from vaultbot.infra.approval import ApprovalManager, ApprovalStatus
from vaultbot.infra.cache import GeneralCache


class TestApprovalManager:
    def test_create(self) -> None:
        mgr = ApprovalManager()
        req = mgr.create("deploy", requester="user1")
        assert req.status == ApprovalStatus.PENDING

    def test_approve(self) -> None:
        mgr = ApprovalManager()
        req = mgr.create("deploy")
        assert mgr.approve(req.request_id, approver="admin") is True
        assert req.status == ApprovalStatus.APPROVED

    def test_deny(self) -> None:
        mgr = ApprovalManager()
        req = mgr.create("deploy")
        assert mgr.deny(req.request_id) is True
        assert req.status == ApprovalStatus.DENIED

    def test_list_pending(self) -> None:
        mgr = ApprovalManager()
        mgr.create("a")
        mgr.create("b")
        req = mgr.create("c")
        mgr.approve(req.request_id)
        assert mgr.pending_count == 2


class TestGeneralCache:
    def test_set_and_get(self) -> None:
        cache = GeneralCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_miss(self) -> None:
        cache = GeneralCache()
        assert cache.get("nope") is None

    def test_ttl_expiry(self) -> None:
        cache = GeneralCache(default_ttl=0)
        cache.set("key", "value")
        assert cache.get("key") is None

    def test_delete(self) -> None:
        cache = GeneralCache()
        cache.set("key", "value")
        assert cache.delete("key") is True
        assert cache.size == 0

    def test_eviction(self) -> None:
        cache = GeneralCache(max_entries=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.size == 2

    def test_clear(self) -> None:
        cache = GeneralCache()
        cache.set("a", 1)
        cache.clear()
        assert cache.size == 0
