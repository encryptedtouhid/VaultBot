"""Detect and flag risky tool invocations before execution.

Each tool call is checked against a registry of known dangerous patterns.
Calls that match are flagged with a risk level and reason so the caller
can decide whether to block, prompt for confirmation, or allow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ToolRisk:
    tool_name: str
    risk_level: RiskLevel
    reasons: tuple[str, ...] = ()
    blocked: bool = False


@dataclass(frozen=True, slots=True)
class DangerousPattern:
    name: str
    tool_pattern: str
    arg_pattern: str = ""
    risk_level: RiskLevel = RiskLevel.HIGH
    reason: str = ""


_DEFAULT_PATTERNS: list[DangerousPattern] = [
    DangerousPattern(
        name="shell_exec",
        tool_pattern=r"^(shell|exec|run|bash|sh)$",
        risk_level=RiskLevel.CRITICAL,
        reason="Direct shell execution",
    ),
    DangerousPattern(
        name="file_delete",
        tool_pattern=r"^(file_delete|rm|remove)$",
        risk_level=RiskLevel.HIGH,
        reason="File deletion",
    ),
    DangerousPattern(
        name="network_request",
        tool_pattern=r"^(http_request|curl|wget|fetch)$",
        risk_level=RiskLevel.MEDIUM,
        reason="Outbound network request",
    ),
    DangerousPattern(
        name="env_modify",
        tool_pattern=r"^(set_env|env_write|putenv)$",
        risk_level=RiskLevel.HIGH,
        reason="Environment variable modification",
    ),
    DangerousPattern(
        name="credential_access",
        tool_pattern=r".*",
        arg_pattern=r"(password|secret|token|api_key|private_key)",
        risk_level=RiskLevel.HIGH,
        reason="Credential parameter detected",
    ),
    DangerousPattern(
        name="sudo",
        tool_pattern=r".*",
        arg_pattern=r"\bsudo\b",
        risk_level=RiskLevel.CRITICAL,
        reason="Elevated privilege request",
    ),
]


@dataclass(slots=True)
class DangerousToolDetector:
    """Checks tool invocations against dangerous patterns."""

    _patterns: list[DangerousPattern] = field(default_factory=list)
    _block_critical: bool = True
    _check_count: int = 0

    def __post_init__(self) -> None:
        if not self._patterns:
            self._patterns = list(_DEFAULT_PATTERNS)

    def add_pattern(self, pattern: DangerousPattern) -> None:
        """Register a custom dangerous pattern."""
        self._patterns.append(pattern)

    def assess(
        self,
        tool_name: str,
        args: dict[str, str] | None = None,
    ) -> ToolRisk:
        """Assess the risk of a tool invocation."""
        self._check_count += 1
        reasons: list[str] = []
        highest = RiskLevel.SAFE
        args_flat = args or {}
        args_str = " ".join(
            f"{k} {v}" for k, v in args_flat.items()
        )

        for pat in self._patterns:
            name_match = re.search(
                pat.tool_pattern, tool_name, re.IGNORECASE,
            )
            arg_match = (
                re.search(pat.arg_pattern, args_str, re.IGNORECASE)
                if pat.arg_pattern
                else None
            )
            if name_match and not pat.arg_pattern:
                reasons.append(pat.reason)
                highest = _max_risk(highest, pat.risk_level)
            elif pat.arg_pattern and arg_match:
                reasons.append(pat.reason)
                highest = _max_risk(highest, pat.risk_level)

        blocked = self._block_critical and highest == RiskLevel.CRITICAL
        if reasons:
            logger.warning(
                "dangerous_tool_detected",
                tool=tool_name,
                risk=highest.value,
                reasons=reasons,
                blocked=blocked,
            )
        return ToolRisk(
            tool_name=tool_name,
            risk_level=highest,
            reasons=tuple(reasons),
            blocked=blocked,
        )

    def is_safe(
        self,
        tool_name: str,
        args: dict[str, str] | None = None,
    ) -> bool:
        """Convenience: return True only when risk is SAFE or LOW."""
        risk = self.assess(tool_name, args)
        return risk.risk_level in (RiskLevel.SAFE, RiskLevel.LOW)

    @property
    def check_count(self) -> int:
        return self._check_count


_RISK_ORDER = {
    RiskLevel.SAFE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    """Return the higher of two risk levels."""
    return a if _RISK_ORDER[a] >= _RISK_ORDER[b] else b
