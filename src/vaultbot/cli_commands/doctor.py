"""Doctor/diagnostics CLI commands."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CheckStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    name: str
    status: CheckStatus
    message: str = ""
    details: str = ""


class DoctorCommands:
    """Diagnostic health check commands."""

    def run_all(self) -> list[DiagnosticCheck]:
        """Run all diagnostic checks."""
        checks: list[DiagnosticCheck] = []
        checks.append(self.check_python())
        checks.append(self.check_config_dir())
        checks.append(self.check_dependencies())
        return checks

    def check_python(self) -> DiagnosticCheck:
        version = sys.version_info
        if version >= (3, 11):
            return DiagnosticCheck(
                name="Python version",
                status=CheckStatus.OK,
                message=f"Python {version.major}.{version.minor}.{version.micro}",
            )
        return DiagnosticCheck(
            name="Python version",
            status=CheckStatus.ERROR,
            message=f"Python {version.major}.{version.minor} (3.11+ required)",
        )

    def check_config_dir(self) -> DiagnosticCheck:
        config_dir = Path.home() / ".vaultbot"
        if config_dir.exists():
            return DiagnosticCheck(
                name="Config directory",
                status=CheckStatus.OK,
                message=str(config_dir),
            )
        return DiagnosticCheck(
            name="Config directory",
            status=CheckStatus.WARNING,
            message="Not found (will be created on first run)",
        )

    def check_dependencies(self) -> DiagnosticCheck:
        missing: list[str] = []
        for pkg in ["httpx", "pydantic", "structlog", "yaml"]:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        if missing:
            return DiagnosticCheck(
                name="Dependencies",
                status=CheckStatus.ERROR,
                message=f"Missing: {', '.join(missing)}",
            )
        return DiagnosticCheck(
            name="Dependencies",
            status=CheckStatus.OK,
            message="All core dependencies available",
        )

    def format_report(self, checks: list[DiagnosticCheck]) -> str:
        lines = ["VaultBot Health Report", "=" * 40]
        for check in checks:
            icon = {"ok": "✓", "warning": "⚠", "error": "✗"}[check.status.value]
            lines.append(f"  {icon} {check.name}: {check.message}")
        ok = sum(1 for c in checks if c.status == CheckStatus.OK)
        lines.append(f"\n{ok}/{len(checks)} checks passed")
        return "\n".join(lines)
