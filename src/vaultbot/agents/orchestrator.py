"""Multi-agent orchestration with workspace mapping and lifecycle."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUSPENDED = "suspended"
    STOPPED = "stopped"


@dataclass(slots=True)
class AgentConfig:
    agent_id: str = ""
    name: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    thinking_enabled: bool = False
    skills: list[str] = field(default_factory=list)
    workspace: str = ""


@dataclass(slots=True)
class AgentInstance:
    config: AgentConfig = field(default_factory=AgentConfig)
    state: AgentState = AgentState.IDLE
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    run_count: int = 0
    parent_id: str = ""
    children: list[str] = field(default_factory=list)


class AgentOrchestrator:
    """Manages multiple agents with workspace isolation and lifecycle."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentInstance] = {}
        self._default_agent: str = ""

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    def register(self, config: AgentConfig) -> AgentInstance:
        instance = AgentInstance(config=config)
        self._agents[config.agent_id] = instance
        if not self._default_agent:
            self._default_agent = config.agent_id
        logger.info("agent_registered", agent_id=config.agent_id)
        return instance

    def get(self, agent_id: str) -> AgentInstance | None:
        return self._agents.get(agent_id)

    def resolve(self, agent_id: str = "") -> AgentInstance | None:
        """Resolve agent by ID or fall back to default."""
        aid = agent_id or self._default_agent
        return self._agents.get(aid)

    def start(self, agent_id: str) -> bool:
        inst = self._agents.get(agent_id)
        if not inst:
            return False
        inst.state = AgentState.RUNNING
        inst.run_count += 1
        inst.last_activity = time.time()
        return True

    def stop(self, agent_id: str) -> bool:
        inst = self._agents.get(agent_id)
        if not inst:
            return False
        inst.state = AgentState.STOPPED
        return True

    def spawn_child(self, parent_id: str, child_config: AgentConfig) -> AgentInstance | None:
        parent = self._agents.get(parent_id)
        if not parent:
            return None
        child = AgentInstance(config=child_config, parent_id=parent_id)
        self._agents[child_config.agent_id] = child
        parent.children.append(child_config.agent_id)
        logger.info("agent_spawned", parent=parent_id, child=child_config.agent_id)
        return child

    def get_children(self, agent_id: str) -> list[AgentInstance]:
        inst = self._agents.get(agent_id)
        if not inst:
            return []
        return [self._agents[cid] for cid in inst.children if cid in self._agents]

    def unregister(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            if self._default_agent == agent_id:
                self._default_agent = next(iter(self._agents), "")
            return True
        return False

    def list_agents(self, state: AgentState | None = None) -> list[AgentInstance]:
        if state:
            return [a for a in self._agents.values() if a.state == state]
        return list(self._agents.values())
