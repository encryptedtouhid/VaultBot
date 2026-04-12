"""Command analysis, safety rules, and execution approval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class SecurityLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalDecision(str, Enum):
    AUTO_APPROVE = "auto_approve"
    ASK_USER = "ask_user"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class CommandAnalysis:
    command: list[str]
    security_level: SecurityLevel
    decision: ApprovalDecision
    reason: str = ""
    matched_rule: str = ""


# Safety rules: (pattern, security_level, decision)
_SAFETY_RULES: list[tuple[str, SecurityLevel, ApprovalDecision]] = [
    (
        r"^(echo|cat|ls|pwd|head|tail|wc|sort|grep|find|date|whoami)$",
        SecurityLevel.SAFE,
        ApprovalDecision.AUTO_APPROVE,
    ),
    (r"^(python3?|node|git|pip|npm|cargo|go)$", SecurityLevel.LOW, ApprovalDecision.AUTO_APPROVE),
    (r"^(curl|wget|ssh|scp)$", SecurityLevel.MEDIUM, ApprovalDecision.ASK_USER),
    (r"^(rm|mv|cp|chmod|chown|kill|pkill)$", SecurityLevel.HIGH, ApprovalDecision.ASK_USER),
    (
        r"^(dd|mkfs|fdisk|mount|umount|shutdown|reboot|systemctl)$",
        SecurityLevel.CRITICAL,
        ApprovalDecision.DENY,
    ),
]


class ExecApprovalEngine:
    """Analyzes commands and determines approval requirements."""

    def __init__(self) -> None:
        self._custom_rules: list[tuple[str, SecurityLevel, ApprovalDecision]] = []
        self._approval_log: list[CommandAnalysis] = []

    def analyze(self, command: list[str]) -> CommandAnalysis:
        if not command:
            return CommandAnalysis(
                command=command,
                security_level=SecurityLevel.CRITICAL,
                decision=ApprovalDecision.DENY,
                reason="Empty command",
            )
        binary = command[0].split("/")[-1]

        # Check custom rules first
        for pattern, level, decision in self._custom_rules:
            if re.match(pattern, binary):
                analysis = CommandAnalysis(
                    command=command,
                    security_level=level,
                    decision=decision,
                    matched_rule=pattern,
                )
                self._approval_log.append(analysis)
                return analysis

        # Check built-in rules
        for pattern, level, decision in _SAFETY_RULES:
            if re.match(pattern, binary):
                analysis = CommandAnalysis(
                    command=command,
                    security_level=level,
                    decision=decision,
                    matched_rule=pattern,
                )
                self._approval_log.append(analysis)
                return analysis

        # Unknown commands need approval
        analysis = CommandAnalysis(
            command=command,
            security_level=SecurityLevel.MEDIUM,
            decision=ApprovalDecision.ASK_USER,
            reason="Unknown command",
        )
        self._approval_log.append(analysis)
        return analysis

    def add_rule(self, pattern: str, level: SecurityLevel, decision: ApprovalDecision) -> None:
        self._custom_rules.append((pattern, level, decision))

    def get_approval_log(self, limit: int = 50) -> list[CommandAnalysis]:
        return self._approval_log[-limit:]

    @property
    def log_count(self) -> int:
        return len(self._approval_log)
