"""Auto-reply and smart routing rules.

Configure automatic responses based on patterns and route messages
to different LLM models based on content type.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AutoReplyRule:
    name: str
    pattern: str
    response: str
    enabled: bool = True
    case_sensitive: bool = False


@dataclass
class RoutingRule:
    name: str
    pattern: str
    target_model: str
    priority: int = 0


class AutoReplyEngine:
    def __init__(self) -> None:
        self._rules: list[AutoReplyRule] = []
        self._routing_rules: list[RoutingRule] = []

    def add_reply_rule(self, rule: AutoReplyRule) -> None:
        self._rules.append(rule)

    def add_routing_rule(self, rule: RoutingRule) -> None:
        self._routing_rules.append(rule)
        self._routing_rules.sort(key=lambda r: r.priority)

    def check_auto_reply(self, text: str) -> str | None:
        for rule in self._rules:
            if not rule.enabled:
                continue
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            if re.search(rule.pattern, text, flags):
                return rule.response
        return None

    def get_model_for_message(self, text: str) -> str | None:
        for rule in self._routing_rules:
            if re.search(rule.pattern, text, re.IGNORECASE):
                return rule.target_model
        return None

    def list_reply_rules(self) -> list[AutoReplyRule]:
        return list(self._rules)

    def list_routing_rules(self) -> list[RoutingRule]:
        return list(self._routing_rules)

    def remove_reply_rule(self, name: str) -> bool:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        return len(self._rules) < before
