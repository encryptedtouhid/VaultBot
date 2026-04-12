"""Status and diagnostics CLI commands."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SystemStatus:
    python_version: str = ""
    package_version: str = "0.1.0"
    platforms_active: list[str] = field(default_factory=list)
    uptime_seconds: float = 0.0
    memory_mb: float = 0.0


class StatusCommands:
    """CLI commands for system status and diagnostics."""

    def __init__(self, version: str = "0.1.0") -> None:
        self._version = version

    def get_status(self) -> SystemStatus:
        return SystemStatus(
            python_version=sys.version.split()[0],
            package_version=self._version,
        )

    def get_version(self) -> str:
        return self._version

    def check_health(self) -> dict[str, bool]:
        return {
            "python_ok": sys.version_info >= (3, 11),
            "config_dir": True,
        }

    def get_diagnostics(self) -> dict[str, str]:
        return {
            "python": sys.version,
            "platform": sys.platform,
            "version": self._version,
        }
