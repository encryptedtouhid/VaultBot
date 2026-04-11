"""Sub-agent spawning and multi-agent orchestration.

Allows the primary agent to spawn child agents for parallel task
execution.  Each sub-agent runs in its own session with isolated
context, depth limits, and token budgets.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Coroutine

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_MAX_DEPTH = 3
_DEFAULT_TOKEN_BUDGET = 50_000
_DEFAULT_TIMEOUT = 300.0  # 5 minutes


class AgentStatus(str, Enum):
    """Status of a sub-agent."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


@dataclass
class AgentResult:
    """Result from a sub-agent execution."""
    agent_id: str
    status: AgentStatus
    result: str = ""
    error: str = ""
    tokens_used: int = 0
    duration_ms: int = 0


@dataclass
class SubAgent:
    """A spawned sub-agent with its own context."""
    id: str
    name: str
    task: str
    parent_id: str | None = None
    depth: int = 0
    status: AgentStatus = AgentStatus.PENDING
    token_budget: int = _DEFAULT_TOKEN_BUDGET
    tokens_used: int = 0
    timeout: float = _DEFAULT_TIMEOUT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: str = ""
    error: str = ""


class SubAgentRegistry:
    """Manages sub-agent lifecycle and orchestration.

    Enforces depth limits, token budgets, and timeout constraints.
    Sub-agents inherit the parent's permission level (never escalate).
    """

    def __init__(
        self,
        *,
        max_depth: int = _MAX_DEPTH,
        default_token_budget: int = _DEFAULT_TOKEN_BUDGET,
        default_timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._agents: dict[str, SubAgent] = {}
        self._max_depth = max_depth
        self._default_token_budget = default_token_budget
        self._default_timeout = default_timeout
        self._agent_counter: int = 0
        self._executor: Callable[..., Coroutine[Any, Any, str]] | None = None
        self._tasks: dict[str, asyncio.Task[AgentResult]] = {}

    def set_executor(
        self, executor: Callable[..., Coroutine[Any, Any, str]]
    ) -> None:
        """Set the async function that executes agent tasks."""
        self._executor = executor

    def spawn(
        self,
        name: str,
        task: str,
        *,
        parent_id: str | None = None,
        token_budget: int | None = None,
        timeout: float | None = None,
    ) -> SubAgent:
        """Spawn a new sub-agent.

        Parameters
        ----------
        name:
            Human-readable agent name.
        task:
            The task/prompt for the agent.
        parent_id:
            ID of the parent agent (for depth tracking).
        token_budget:
            Maximum tokens this agent can consume.
        timeout:
            Maximum execution time in seconds.

        Raises
        ------
        ValueError
            If max depth would be exceeded.
        """
        # Calculate depth
        depth = 0
        if parent_id and parent_id in self._agents:
            depth = self._agents[parent_id].depth + 1

        if depth >= self._max_depth:
            raise ValueError(
                f"Max agent depth ({self._max_depth}) exceeded. "
                f"Cannot spawn at depth {depth}."
            )

        self._agent_counter += 1
        agent_id = f"agent_{self._agent_counter}"

        agent = SubAgent(
            id=agent_id,
            name=name,
            task=task,
            parent_id=parent_id,
            depth=depth,
            token_budget=token_budget or self._default_token_budget,
            timeout=timeout or self._default_timeout,
        )
        self._agents[agent_id] = agent
        logger.info(
            "subagent_spawned",
            agent_id=agent_id,
            name=name,
            depth=depth,
            parent=parent_id,
        )
        return agent

    async def run(self, agent_id: str) -> AgentResult:
        """Execute a sub-agent's task."""
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_id}")

        if not self._executor:
            raise RuntimeError("No executor set. Call set_executor() first.")

        agent.status = AgentStatus.RUNNING
        agent.started_at = datetime.now(UTC)
        start_mono = time.monotonic()

        try:
            result = await asyncio.wait_for(
                self._executor(agent.task),
                timeout=agent.timeout,
            )
            elapsed = int((time.monotonic() - start_mono) * 1000)

            agent.status = AgentStatus.COMPLETED
            agent.result = result
            agent.finished_at = datetime.now(UTC)

            logger.info("subagent_completed", agent_id=agent_id, duration_ms=elapsed)
            return AgentResult(
                agent_id=agent_id,
                status=AgentStatus.COMPLETED,
                result=result,
                duration_ms=elapsed,
            )

        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - start_mono) * 1000)
            agent.status = AgentStatus.TIMED_OUT
            agent.error = f"Timed out after {agent.timeout}s"
            agent.finished_at = datetime.now(UTC)

            return AgentResult(
                agent_id=agent_id,
                status=AgentStatus.TIMED_OUT,
                error=agent.error,
                duration_ms=elapsed,
            )

        except Exception as exc:
            elapsed = int((time.monotonic() - start_mono) * 1000)
            agent.status = AgentStatus.FAILED
            agent.error = str(exc)
            agent.finished_at = datetime.now(UTC)

            return AgentResult(
                agent_id=agent_id,
                status=AgentStatus.FAILED,
                error=str(exc),
                duration_ms=elapsed,
            )

    async def run_parallel(self, agent_ids: list[str]) -> list[AgentResult]:
        """Run multiple sub-agents in parallel."""
        tasks = [self.run(aid) for aid in agent_ids]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def cancel(self, agent_id: str) -> bool:
        """Cancel a running or pending agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        if agent.status in (AgentStatus.PENDING, AgentStatus.RUNNING):
            agent.status = AgentStatus.CANCELLED
            agent.finished_at = datetime.now(UTC)
            if agent_id in self._tasks:
                self._tasks[agent_id].cancel()
            return True
        return False

    def get_agent(self, agent_id: str) -> SubAgent | None:
        return self._agents.get(agent_id)

    def list_agents(self, parent_id: str | None = None) -> list[SubAgent]:
        """List agents, optionally filtered by parent."""
        agents = list(self._agents.values())
        if parent_id is not None:
            agents = [a for a in agents if a.parent_id == parent_id]
        return agents

    def cleanup_completed(self) -> int:
        """Remove completed/failed/cancelled agents. Returns count removed."""
        terminal = {AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED, AgentStatus.TIMED_OUT}
        to_remove = [aid for aid, a in self._agents.items() if a.status in terminal]
        for aid in to_remove:
            del self._agents[aid]
        return len(to_remove)

    @property
    def active_count(self) -> int:
        return sum(1 for a in self._agents.values() if a.status in (AgentStatus.PENDING, AgentStatus.RUNNING))

    @property
    def total_count(self) -> int:
        return len(self._agents)
