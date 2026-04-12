"""Dynamic policy for sandbox tool access."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ToolAccess(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True, slots=True)
class ToolPolicyRule:
    tool_name: str
    access: ToolAccess = ToolAccess.ALLOW
    reason: str = ""


class ToolPolicy:
    """Dynamic policy for controlling tool access within a sandbox."""

    def __init__(self) -> None:
        self._rules: dict[str, ToolPolicyRule] = {}
        self._default_access = ToolAccess.ALLOW

    def add_rule(self, rule: ToolPolicyRule) -> None:
        self._rules[rule.tool_name] = rule

    def remove_rule(self, tool_name: str) -> bool:
        if tool_name in self._rules:
            del self._rules[tool_name]
            return True
        return False

    def evaluate(self, tool_name: str) -> ToolAccess:
        rule = self._rules.get(tool_name)
        if rule:
            return rule.access
        return self._default_access

    def set_default(self, access: ToolAccess) -> None:
        self._default_access = access

    def list_rules(self) -> list[ToolPolicyRule]:
        return list(self._rules.values())

    @property
    def rule_count(self) -> int:
        return len(self._rules)
