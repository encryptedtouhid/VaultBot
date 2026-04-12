"""Message routing engine with binding resolution and account lookup."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class BindingScope(str, Enum):
    EXPLICIT_PEER = "explicit_peer"
    PARENT_PEER = "parent_peer"
    WILDCARD = "wildcard"
    GUILD_ROLES = "guild_roles"
    GUILD = "guild"
    TEAM = "team"
    ACCOUNT = "account"
    CHANNEL = "channel"
    DEFAULT = "default"


class ChatType(str, Enum):
    DM = "dm"
    GROUP = "group"
    THREAD = "thread"
    CHANNEL = "channel"


@dataclass(frozen=True, slots=True)
class RouteBinding:
    scope: BindingScope
    agent_id: str
    channel: str = ""
    account: str = ""
    peer: str = ""
    role: str = ""
    priority: int = 0


@dataclass(frozen=True, slots=True)
class RouteResult:
    agent_id: str
    session_key: str
    binding_scope: BindingScope
    chat_type: ChatType = ChatType.CHANNEL


def derive_session_key(agent_id: str, chat_type: ChatType, chat_id: str) -> str:
    """Build a session key from agent, chat type, and chat ID."""
    return f"agent:{agent_id}:{chat_type.value}:{chat_id}"


def normalize_account(account: str) -> str:
    """Normalize account ID (case-insensitive, strip whitespace)."""
    return account.strip().lower()


class RouteResolver:
    """Resolves message routes using binding priority chains."""

    def __init__(self) -> None:
        self._bindings: list[RouteBinding] = []

    def add_binding(self, binding: RouteBinding) -> None:
        self._bindings.append(binding)
        self._bindings.sort(key=lambda b: b.scope.value)

    def remove_binding(self, agent_id: str, channel: str = "") -> int:
        before = len(self._bindings)
        self._bindings = [
            b
            for b in self._bindings
            if not (b.agent_id == agent_id and (not channel or b.channel == channel))
        ]
        return before - len(self._bindings)

    def resolve(
        self,
        channel: str,
        account: str = "",
        peer: str = "",
        role: str = "",
        chat_type: ChatType = ChatType.CHANNEL,
    ) -> RouteResult | None:
        """Resolve the best-matching route for a message context."""
        norm_account = normalize_account(account) if account else ""

        # Priority: peer > parent > wildcard > roles > account > channel > default
        candidates: list[tuple[int, RouteBinding]] = []
        for binding in self._bindings:
            score = 0
            if binding.peer and binding.peer == peer:
                score = 100
            elif binding.role and binding.role == role:
                score = 60
            elif binding.account and normalize_account(binding.account) == norm_account:
                score = 40
            elif binding.channel and binding.channel == channel:
                score = 20
            elif binding.scope == BindingScope.DEFAULT:
                score = 1
            else:
                continue
            candidates.append((score + binding.priority, binding))

        if not candidates:
            return None

        best = max(candidates, key=lambda c: c[0])
        binding = best[1]
        session_key = derive_session_key(binding.agent_id, chat_type, peer or channel)
        return RouteResult(
            agent_id=binding.agent_id,
            session_key=session_key,
            binding_scope=binding.scope,
            chat_type=chat_type,
        )

    @property
    def binding_count(self) -> int:
        return len(self._bindings)
