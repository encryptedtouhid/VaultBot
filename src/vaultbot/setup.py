"""Setup wizard and doctor/health diagnostic for VaultBot.

Provides interactive first-run setup and diagnostic commands to
verify configuration, credentials, and connectivity.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.config import CONFIG_DIR, CONFIG_FILE
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class CheckStatus(str, Enum):
    """Status of a diagnostic check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    """Result of a single diagnostic check."""

    name: str
    status: CheckStatus
    message: str
    fix_hint: str = ""


@dataclass
class DiagnosticReport:
    """Complete diagnostic report."""

    checks: list[DiagnosticCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.status in (CheckStatus.PASS, CheckStatus.SKIP) for c in self.checks)

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.WARN)


class Doctor:
    """Diagnostic tool for VaultBot health checking."""

    def run_all(self) -> DiagnosticReport:
        """Run all diagnostic checks."""
        report = DiagnosticReport()
        report.checks.append(self.check_python_version())
        report.checks.append(self.check_config_dir())
        report.checks.append(self.check_config_file())
        report.checks.append(self.check_config_permissions())
        report.checks.append(self.check_dependencies())
        return report

    def check_python_version(self) -> DiagnosticCheck:
        """Check Python version >= 3.11."""
        version = sys.version_info
        if version >= (3, 11):
            return DiagnosticCheck(
                name="Python version",
                status=CheckStatus.PASS,
                message=f"Python {version.major}.{version.minor}.{version.micro}",
            )
        return DiagnosticCheck(
            name="Python version",
            status=CheckStatus.FAIL,
            message=f"Python {version.major}.{version.minor} (need >= 3.11)",
            fix_hint="Install Python 3.11+: https://python.org/downloads",
        )

    def check_config_dir(self) -> DiagnosticCheck:
        """Check if config directory exists."""
        if CONFIG_DIR.exists():
            return DiagnosticCheck(
                name="Config directory",
                status=CheckStatus.PASS,
                message=str(CONFIG_DIR),
            )
        return DiagnosticCheck(
            name="Config directory",
            status=CheckStatus.WARN,
            message=f"{CONFIG_DIR} does not exist",
            fix_hint="Run 'vaultbot init' to create it.",
        )

    def check_config_file(self) -> DiagnosticCheck:
        """Check if config file exists and is valid YAML."""
        if not CONFIG_FILE.exists():
            return DiagnosticCheck(
                name="Config file",
                status=CheckStatus.WARN,
                message="No config file (using defaults)",
                fix_hint="Run 'vaultbot init' to create config.yaml",
            )

        try:
            import yaml

            with open(CONFIG_FILE) as f:
                yaml.safe_load(f)
            return DiagnosticCheck(
                name="Config file",
                status=CheckStatus.PASS,
                message=str(CONFIG_FILE),
            )
        except Exception as exc:
            return DiagnosticCheck(
                name="Config file",
                status=CheckStatus.FAIL,
                message=f"Invalid YAML: {exc}",
                fix_hint="Check config.yaml syntax.",
            )

    def check_config_permissions(self) -> DiagnosticCheck:
        """Check config file permissions."""
        if not CONFIG_FILE.exists():
            return DiagnosticCheck(
                name="Config permissions",
                status=CheckStatus.SKIP,
                message="No config file",
            )

        mode = CONFIG_FILE.stat().st_mode & 0o777
        if mode & 0o077:
            return DiagnosticCheck(
                name="Config permissions",
                status=CheckStatus.WARN,
                message=f"Permissions {oct(mode)} (should be 0600)",
                fix_hint=f"chmod 600 {CONFIG_FILE}",
            )
        return DiagnosticCheck(
            name="Config permissions",
            status=CheckStatus.PASS,
            message=f"Permissions {oct(mode)}",
        )

    def check_dependencies(self) -> DiagnosticCheck:
        """Check if required dependencies are installed."""
        missing: list[str] = []
        for module in ["httpx", "pydantic", "yaml", "structlog", "cryptography"]:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)

        if missing:
            return DiagnosticCheck(
                name="Dependencies",
                status=CheckStatus.FAIL,
                message=f"Missing: {', '.join(missing)}",
                fix_hint="pip install vaultbot",
            )
        return DiagnosticCheck(
            name="Dependencies",
            status=CheckStatus.PASS,
            message="All required packages installed",
        )


class SetupWizard:
    """Interactive first-run setup wizard."""

    def __init__(self) -> None:
        self._steps_completed: list[str] = []

    def is_first_run(self) -> bool:
        """Check if this is a first run (no config exists)."""
        return not CONFIG_FILE.exists()

    def create_config_dir(self) -> bool:
        """Create the config directory."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
            self._steps_completed.append("config_dir")
            return True
        except OSError:
            return False

    def create_default_config(self) -> bool:
        """Create a default config file."""
        try:
            from vaultbot.config import VaultBotConfig

            config = VaultBotConfig()
            config.save()
            self._steps_completed.append("config_file")
            return True
        except Exception:
            return False

    @property
    def steps_completed(self) -> list[str]:
        return list(self._steps_completed)
