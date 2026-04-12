"""ACP permission policies and runtime controls."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PolicyAction(str, Enum):
    """Actions that can be policy-controlled."""

    SEND_MESSAGE = "send_message"
    EXECUTE_TOOL = "execute_tool"
    ACCESS_FILE = "access_file"
    SPAWN_AGENT = "spawn_agent"
    MODIFY_CONFIG = "modify_config"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """Rate limit configuration for a session."""

    max_turns_per_minute: int = 30
    max_tokens_per_turn: int = 8192
    max_concurrent_tasks: int = 5
    timeout_seconds: float = 300.0


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    """Combined policy for an ACP session."""

    rate_limit: RateLimitPolicy = field(default_factory=RateLimitPolicy)
    allowed_actions: set[PolicyAction] = field(default_factory=lambda: set(PolicyAction))
    denied_actions: set[PolicyAction] = field(default_factory=set)
    require_approval_for: set[PolicyAction] = field(default_factory=set)


class PolicyEngine:
    """Evaluates policies against session actions."""

    def __init__(self) -> None:
        self._policies: dict[str, SessionPolicy] = {}
        self._default_policy = SessionPolicy()

    def set_policy(self, session_id: str, policy: SessionPolicy) -> None:
        self._policies[session_id] = policy

    def get_policy(self, session_id: str) -> SessionPolicy:
        return self._policies.get(session_id, self._default_policy)

    def evaluate(self, session_id: str, action: PolicyAction) -> PolicyDecision:
        """Evaluate whether an action is allowed for a session."""
        policy = self.get_policy(session_id)
        if action in policy.denied_actions:
            return PolicyDecision.DENY
        if action in policy.require_approval_for:
            return PolicyDecision.REQUIRE_APPROVAL
        if action in policy.allowed_actions:
            return PolicyDecision.ALLOW
        return PolicyDecision.ALLOW

    def check_rate_limit(self, session_id: str, current_turns: int) -> bool:
        """Check if session is within rate limits."""
        policy = self.get_policy(session_id)
        return current_turns < policy.rate_limit.max_turns_per_minute

    def remove_policy(self, session_id: str) -> bool:
        if session_id in self._policies:
            del self._policies[session_id]
            return True
        return False
