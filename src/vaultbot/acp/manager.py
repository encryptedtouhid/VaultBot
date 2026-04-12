"""Core ACP manager orchestrating sessions, policies, tasks, and provenance."""

from __future__ import annotations

from vaultbot.acp.bindings import BindingRegistry
from vaultbot.acp.policy import PolicyAction, PolicyDecision, PolicyEngine, SessionPolicy
from vaultbot.acp.provenance import ProvenanceMode, ProvenanceTracker
from vaultbot.acp.session import ACPSession, ACPSessionStore, SessionIdentity
from vaultbot.acp.task_executor import ACPTaskExecutor
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ACPManager:
    """Orchestrates the full Approval Control Plane."""

    def __init__(
        self,
        max_sessions: int = 5000,
        provenance_mode: ProvenanceMode = ProvenanceMode.META,
    ) -> None:
        self.sessions = ACPSessionStore(max_sessions=max_sessions)
        self.policies = PolicyEngine()
        self.tasks = ACPTaskExecutor()
        self.provenance = ProvenanceTracker(mode=provenance_mode)
        self.bindings = BindingRegistry()

    def create_session(
        self, user_id: str = "", platform: str = "", policy: SessionPolicy | None = None
    ) -> ACPSession:
        identity = SessionIdentity(user_id=user_id, platform=platform)
        session = self.sessions.create(identity=identity)
        if policy:
            self.policies.set_policy(session.session_id, policy)
        self.provenance.record(session.session_id, "session_created", actor=user_id)
        return session

    def request_action(
        self, session_id: str, action: PolicyAction, actor: str = ""
    ) -> PolicyDecision:
        decision = self.policies.evaluate(session_id, action)
        self.provenance.record(
            session_id,
            f"action_requested:{action.value}",
            actor=actor,
            metadata={"decision": decision.value},
        )
        session = self.sessions.get(session_id)
        if session:
            session.touch()
        return decision

    def close_session(self, session_id: str) -> bool:
        self.provenance.record(session_id, "session_closed")
        self.policies.remove_policy(session_id)
        self.bindings.clear_session(session_id)
        return self.sessions.close(session_id)

    def run_maintenance(self) -> dict[str, int]:
        """Run periodic maintenance: evict expired sessions, check task timeouts."""
        evicted = self.sessions.evict_expired()
        timed_out = self.tasks.check_timeouts()
        return {"sessions_evicted": evicted, "tasks_timed_out": timed_out}
