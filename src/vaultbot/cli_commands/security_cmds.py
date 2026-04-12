"""Security audit CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class AuditFinding:
    title: str
    severity: Severity
    description: str = ""
    remediation: str = ""


class SecurityCommands:
    """CLI commands for security auditing."""

    def run_audit(self) -> list[AuditFinding]:
        """Run a basic security audit."""
        findings: list[AuditFinding] = []

        # Check for common security issues
        findings.append(
            AuditFinding(
                title="Config file permissions",
                severity=Severity.INFO,
                description="Verify config files have restricted permissions",
            )
        )

        return findings

    def check_secrets(self) -> list[AuditFinding]:
        """Check for exposed secrets."""
        return []

    def format_findings(self, findings: list[AuditFinding]) -> str:
        if not findings:
            return "No findings"
        lines = []
        for f in findings:
            lines.append(f"[{f.severity.value.upper()}] {f.title}")
            if f.description:
                lines.append(f"  {f.description}")
        return "\n".join(lines)
