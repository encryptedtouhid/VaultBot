"""Skill contracts with source scoping and lifecycle."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class SkillSource(str, Enum):
    USER = "user"
    PROJECT = "project"
    TEMPORARY = "temporary"
    BUNDLED = "bundled"


class SkillState(str, Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass(slots=True)
class SkillContract:
    name: str
    source: SkillSource = SkillSource.USER
    state: SkillState = SkillState.AVAILABLE
    version: str = "0.1.0"
    description: str = ""
    commands: list[str] = field(default_factory=list)
    required_binaries: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    installed_at: float = field(default_factory=time.time)
    last_used: float = 0.0


class SkillRegistry:
    """Registry for agent skills with eligibility checking."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillContract] = {}

    def register(self, contract: SkillContract) -> None:
        self._skills[contract.name] = contract

    def unregister(self, name: str) -> bool:
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def get(self, name: str) -> SkillContract | None:
        return self._skills.get(name)

    def is_eligible(self, name: str, platform: str = "") -> bool:
        """Check if a skill is eligible for the current context."""
        skill = self._skills.get(name)
        if not skill or skill.state != SkillState.AVAILABLE:
            return False
        if skill.platforms and platform and platform not in skill.platforms:
            return False
        return True

    def list_available(self, platform: str = "") -> list[SkillContract]:
        return [
            s
            for s in self._skills.values()
            if s.state == SkillState.AVAILABLE
            and (not platform or not s.platforms or platform in s.platforms)
        ]

    def activate(self, name: str) -> bool:
        skill = self._skills.get(name)
        if not skill:
            return False
        skill.state = SkillState.ACTIVE
        skill.last_used = time.time()
        return True

    def deactivate(self, name: str) -> bool:
        skill = self._skills.get(name)
        if not skill:
            return False
        skill.state = SkillState.AVAILABLE
        return True

    def filter_for_agent(self, agent_skills: list[str]) -> list[SkillContract]:
        """Filter skills to those allowed for a specific agent."""
        return [self._skills[name] for name in agent_skills if name in self._skills]

    @property
    def skill_count(self) -> int:
        return len(self._skills)
