"""Agent management CLI commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentInfo:
    agent_id: str
    name: str = ""
    model: str = ""
    status: str = "idle"


class AgentCommands:
    """CLI commands for agent management."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentInfo] = {}

    def create(self, agent_id: str, name: str = "", model: str = "") -> AgentInfo:
        info = AgentInfo(agent_id=agent_id, name=name or agent_id, model=model)
        self._agents[agent_id] = info
        return info

    def delete(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def list_agents(self) -> list[AgentInfo]:
        return list(self._agents.values())

    def get(self, agent_id: str) -> AgentInfo | None:
        return self._agents.get(agent_id)

    def bind(self, agent_id: str, channel: str) -> bool:
        return agent_id in self._agents
