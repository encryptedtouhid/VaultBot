"""Subagent registry with lifecycle, orphan recovery, and announce queue."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class SubagentRole(str, Enum):
    MAIN = "main"
    ORCHESTRATOR = "orchestrator"
    LEAF = "leaf"


class SubagentState(str, Enum):
    SPAWNING = "spawning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ORPHANED = "orphaned"


@dataclass(slots=True)
class SubagentEntry:
    agent_id: str
    parent_id: str = ""
    role: SubagentRole = SubagentRole.LEAF
    state: SubagentState = SubagentState.SPAWNING
    depth: int = 0
    max_depth: int = 3
    token_budget: int = 50000
    tokens_used: int = 0
    spawned_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    result: str = ""
    error: str = ""


@dataclass(frozen=True, slots=True)
class AnnounceMessage:
    agent_id: str
    parent_id: str
    result: str
    timestamp: float = field(default_factory=time.time)


class SubagentRegistry:
    """Comprehensive subagent lifecycle management."""

    def __init__(self, max_depth: int = 3) -> None:
        self._agents: dict[str, SubagentEntry] = {}
        self._announce_queue: list[AnnounceMessage] = []
        self._max_depth = max_depth

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def announce_queue_size(self) -> int:
        return len(self._announce_queue)

    def can_spawn(self, parent_id: str) -> bool:
        parent = self._agents.get(parent_id)
        if not parent:
            return True  # Root agent
        return parent.depth < self._max_depth

    def spawn(
        self, agent_id: str, parent_id: str = "", role: SubagentRole = SubagentRole.LEAF
    ) -> SubagentEntry | None:
        parent = self._agents.get(parent_id)
        depth = (parent.depth + 1) if parent else 0
        if depth > self._max_depth:
            logger.warning("subagent_depth_exceeded", agent_id=agent_id, depth=depth)
            return None
        entry = SubagentEntry(
            agent_id=agent_id,
            parent_id=parent_id,
            role=role,
            depth=depth,
            max_depth=self._max_depth,
        )
        entry.state = SubagentState.RUNNING
        self._agents[agent_id] = entry
        logger.info("subagent_spawned", agent_id=agent_id, parent=parent_id, depth=depth)
        return entry

    def complete(self, agent_id: str, result: str = "") -> bool:
        entry = self._agents.get(agent_id)
        if not entry or entry.state != SubagentState.RUNNING:
            return False
        entry.state = SubagentState.COMPLETED
        entry.result = result
        entry.completed_at = time.time()
        self._announce_queue.append(
            AnnounceMessage(agent_id=agent_id, parent_id=entry.parent_id, result=result)
        )
        return True

    def fail(self, agent_id: str, error: str = "") -> bool:
        entry = self._agents.get(agent_id)
        if not entry or entry.state != SubagentState.RUNNING:
            return False
        entry.state = SubagentState.FAILED
        entry.error = error
        entry.completed_at = time.time()
        return True

    def get(self, agent_id: str) -> SubagentEntry | None:
        return self._agents.get(agent_id)

    def get_children(self, parent_id: str) -> list[SubagentEntry]:
        return [e for e in self._agents.values() if e.parent_id == parent_id]

    def drain_announce_queue(self) -> list[AnnounceMessage]:
        messages = list(self._announce_queue)
        self._announce_queue.clear()
        return messages

    def recover_orphans(self, timeout_seconds: float = 300.0) -> int:
        """Mark stale running agents as orphaned."""
        now = time.time()
        count = 0
        for entry in self._agents.values():
            if entry.state == SubagentState.RUNNING and (now - entry.spawned_at) > timeout_seconds:
                entry.state = SubagentState.ORPHANED
                count += 1
        return count

    def update_token_usage(self, agent_id: str, tokens: int) -> bool:
        entry = self._agents.get(agent_id)
        if not entry:
            return False
        entry.tokens_used += tokens
        return entry.tokens_used <= entry.token_budget
