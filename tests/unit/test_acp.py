"""Unit tests for Approval Control Plane (ACP)."""

from __future__ import annotations

from vaultbot.acp.bindings import BindingRegistry
from vaultbot.acp.manager import ACPManager
from vaultbot.acp.policy import (
    PolicyAction,
    PolicyDecision,
    PolicyEngine,
    RateLimitPolicy,
    SessionPolicy,
)
from vaultbot.acp.provenance import ProvenanceMode, ProvenanceTracker
from vaultbot.acp.session import (
    ACPSessionState,
    ACPSessionStore,
    IdentityState,
    SessionIdentity,
)
from vaultbot.acp.task_executor import ACPTaskExecutor, TaskState

# ---------------------------------------------------------------------------
# Session Store
# ---------------------------------------------------------------------------


class TestACPSessionStore:
    def test_create_session(self) -> None:
        store = ACPSessionStore()
        session = store.create()
        assert session.state == ACPSessionState.ACTIVE
        assert store.count == 1

    def test_create_with_identity(self) -> None:
        store = ACPSessionStore()
        identity = SessionIdentity(user_id="u1", platform="telegram")
        session = store.create(identity=identity)
        assert session.identity.user_id == "u1"

    def test_get_session(self) -> None:
        store = ACPSessionStore()
        s = store.create()
        assert store.get(s.session_id) is not None
        assert store.get("nope") is None

    def test_close_session(self) -> None:
        store = ACPSessionStore()
        s = store.create()
        assert store.close(s.session_id) is True
        assert store.count == 0

    def test_suspend_and_resume(self) -> None:
        store = ACPSessionStore()
        s = store.create()
        assert store.suspend(s.session_id) is True
        assert s.state == ACPSessionState.SUSPENDED
        assert store.resume(s.session_id) is True
        assert s.state == ACPSessionState.ACTIVE

    def test_suspend_non_active_fails(self) -> None:
        store = ACPSessionStore()
        s = store.create()
        store.suspend(s.session_id)
        assert store.suspend(s.session_id) is False

    def test_reconcile_identity(self) -> None:
        store = ACPSessionStore()
        s = store.create()
        assert store.reconcile_identity(s.session_id, "u1", "discord") is True
        assert s.identity.state == IdentityState.STABLE
        assert s.identity.user_id == "u1"

    def test_evict_expired(self) -> None:
        store = ACPSessionStore()
        s = store.create()
        s.idle_ttl_seconds = 0
        s.last_activity = 0
        evicted = store.evict_expired()
        assert evicted == 1
        assert store.count == 0

    def test_max_sessions_eviction(self) -> None:
        store = ACPSessionStore(max_sessions=2)
        store.create()
        store.create()
        store.create()
        assert store.count == 2

    def test_session_touch(self) -> None:
        store = ACPSessionStore()
        s = store.create()
        old_activity = s.last_activity
        s.touch()
        assert s.last_activity >= old_activity
        assert s.turn_count == 1


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------


class TestPolicyEngine:
    def test_default_allow(self) -> None:
        engine = PolicyEngine()
        decision = engine.evaluate("s1", PolicyAction.SEND_MESSAGE)
        assert decision == PolicyDecision.ALLOW

    def test_deny_action(self) -> None:
        engine = PolicyEngine()
        policy = SessionPolicy(denied_actions={PolicyAction.EXECUTE_TOOL})
        engine.set_policy("s1", policy)
        assert engine.evaluate("s1", PolicyAction.EXECUTE_TOOL) == PolicyDecision.DENY

    def test_require_approval(self) -> None:
        engine = PolicyEngine()
        policy = SessionPolicy(require_approval_for={PolicyAction.MODIFY_CONFIG})
        engine.set_policy("s1", policy)
        assert engine.evaluate("s1", PolicyAction.MODIFY_CONFIG) == PolicyDecision.REQUIRE_APPROVAL

    def test_check_rate_limit(self) -> None:
        engine = PolicyEngine()
        policy = SessionPolicy(rate_limit=RateLimitPolicy(max_turns_per_minute=5))
        engine.set_policy("s1", policy)
        assert engine.check_rate_limit("s1", 3) is True
        assert engine.check_rate_limit("s1", 5) is False

    def test_remove_policy(self) -> None:
        engine = PolicyEngine()
        engine.set_policy("s1", SessionPolicy())
        assert engine.remove_policy("s1") is True
        assert engine.remove_policy("s1") is False


# ---------------------------------------------------------------------------
# Task Executor
# ---------------------------------------------------------------------------


class TestACPTaskExecutor:
    def test_create_task(self) -> None:
        executor = ACPTaskExecutor()
        task = executor.create_task("s1", "test task")
        assert task.state == TaskState.PENDING
        assert executor.task_count == 1

    def test_start_task(self) -> None:
        executor = ACPTaskExecutor()
        task = executor.create_task("s1")
        assert executor.start_task(task.task_id) is True
        assert task.state == TaskState.RUNNING

    def test_update_progress(self) -> None:
        executor = ACPTaskExecutor()
        task = executor.create_task("s1")
        executor.start_task(task.task_id)
        assert executor.update_progress(task.task_id, 0.5) is True
        assert task.progress == 0.5

    def test_complete_task(self) -> None:
        executor = ACPTaskExecutor()
        task = executor.create_task("s1")
        executor.start_task(task.task_id)
        assert executor.complete_task(task.task_id, "done") is True
        assert task.state == TaskState.COMPLETED
        assert task.progress == 1.0

    def test_fail_task(self) -> None:
        executor = ACPTaskExecutor()
        task = executor.create_task("s1")
        executor.start_task(task.task_id)
        assert executor.fail_task(task.task_id, "error") is True
        assert task.state == TaskState.FAILED

    def test_cancel_task(self) -> None:
        executor = ACPTaskExecutor()
        task = executor.create_task("s1")
        assert executor.cancel_task(task.task_id) is True
        assert task.state == TaskState.CANCELLED

    def test_check_timeouts(self) -> None:
        executor = ACPTaskExecutor()
        task = executor.create_task("s1", timeout=0)
        executor.start_task(task.task_id)
        task.started_at = 0
        count = executor.check_timeouts()
        assert count == 1
        assert task.state == TaskState.TIMED_OUT

    def test_get_session_tasks(self) -> None:
        executor = ACPTaskExecutor()
        executor.create_task("s1")
        executor.create_task("s1")
        executor.create_task("s2")
        assert len(executor.get_session_tasks("s1")) == 2


# ---------------------------------------------------------------------------
# Provenance Tracker
# ---------------------------------------------------------------------------


class TestProvenanceTracker:
    def test_record_meta_mode(self) -> None:
        tracker = ProvenanceTracker(mode=ProvenanceMode.META)
        entry = tracker.record("s1", "test_action", actor="user1")
        assert entry is not None
        assert tracker.entry_count == 1

    def test_record_off_mode(self) -> None:
        tracker = ProvenanceTracker(mode=ProvenanceMode.OFF)
        entry = tracker.record("s1", "test_action")
        assert entry is None
        assert tracker.entry_count == 0

    def test_get_session_trail(self) -> None:
        tracker = ProvenanceTracker()
        tracker.record("s1", "a")
        tracker.record("s1", "b")
        tracker.record("s2", "c")
        trail = tracker.get_session_trail("s1")
        assert len(trail) == 2

    def test_clear_session(self) -> None:
        tracker = ProvenanceTracker()
        tracker.record("s1", "a")
        tracker.record("s1", "b")
        cleared = tracker.clear_session("s1")
        assert cleared == 2
        assert tracker.entry_count == 0


# ---------------------------------------------------------------------------
# Binding Registry
# ---------------------------------------------------------------------------


class TestBindingRegistry:
    def test_bind_and_resolve(self) -> None:
        reg = BindingRegistry()
        reg.bind("s1", "agent1", priority=10)
        assert reg.resolve("s1") == "agent1"

    def test_resolve_highest_priority(self) -> None:
        reg = BindingRegistry()
        reg.bind("s1", "low", priority=1)
        reg.bind("s1", "high", priority=10)
        assert reg.resolve("s1") == "high"

    def test_resolve_empty(self) -> None:
        reg = BindingRegistry()
        assert reg.resolve("s1") is None

    def test_unbind(self) -> None:
        reg = BindingRegistry()
        reg.bind("s1", "agent1")
        assert reg.unbind("s1", "agent1") is True
        assert reg.resolve("s1") is None

    def test_clear_session(self) -> None:
        reg = BindingRegistry()
        reg.bind("s1", "a1")
        reg.bind("s1", "a2")
        reg.clear_session("s1")
        assert reg.get_bindings("s1") == []

    def test_total_bindings(self) -> None:
        reg = BindingRegistry()
        reg.bind("s1", "a1")
        reg.bind("s2", "a2")
        assert reg.total_bindings == 2


# ---------------------------------------------------------------------------
# ACP Manager (Integration)
# ---------------------------------------------------------------------------


class TestACPManager:
    def test_create_session(self) -> None:
        mgr = ACPManager()
        session = mgr.create_session(user_id="u1", platform="tg")
        assert session.state == ACPSessionState.ACTIVE
        assert mgr.provenance.entry_count == 1

    def test_create_with_policy(self) -> None:
        mgr = ACPManager()
        policy = SessionPolicy(denied_actions={PolicyAction.EXECUTE_TOOL})
        session = mgr.create_session(policy=policy)
        decision = mgr.request_action(session.session_id, PolicyAction.EXECUTE_TOOL)
        assert decision == PolicyDecision.DENY

    def test_request_action_records_provenance(self) -> None:
        mgr = ACPManager()
        session = mgr.create_session()
        mgr.request_action(session.session_id, PolicyAction.SEND_MESSAGE, actor="u1")
        assert mgr.provenance.entry_count == 2  # create + action

    def test_close_session_cleans_up(self) -> None:
        mgr = ACPManager()
        session = mgr.create_session()
        mgr.bindings.bind(session.session_id, "agent1")
        mgr.close_session(session.session_id)
        assert mgr.sessions.count == 0
        assert mgr.bindings.get_bindings(session.session_id) == []

    def test_maintenance(self) -> None:
        mgr = ACPManager()
        s = mgr.create_session()
        s.idle_ttl_seconds = 0
        s.last_activity = 0
        t = mgr.tasks.create_task(s.session_id, timeout=0)
        mgr.tasks.start_task(t.task_id)
        t.started_at = 0
        result = mgr.run_maintenance()
        assert result["sessions_evicted"] == 1
        assert result["tasks_timed_out"] == 1
