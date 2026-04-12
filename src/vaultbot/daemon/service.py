"""Cross-platform daemon service management."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ServicePlatform(str, Enum):
    LAUNCHD = "launchd"
    SYSTEMD = "systemd"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class ServiceState(str, Enum):
    INSTALLED = "installed"
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_INSTALLED = "not_installed"


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    name: str = "vaultbot"
    description: str = "VaultBot AI Agent Service"
    binary_path: str = ""
    working_dir: str = ""
    auto_restart: bool = True
    log_path: str = ""


def detect_platform() -> ServicePlatform:
    """Detect the current service management platform."""
    if sys.platform == "darwin":
        return ServicePlatform.LAUNCHD
    if sys.platform == "linux":
        return ServicePlatform.SYSTEMD
    if sys.platform == "win32":
        return ServicePlatform.WINDOWS
    return ServicePlatform.UNKNOWN


class ServiceManager:
    """Manages daemon service lifecycle across platforms."""

    def __init__(self, config: ServiceConfig | None = None) -> None:
        self._config = config or ServiceConfig()
        self._platform = detect_platform()
        self._state = ServiceState.NOT_INSTALLED

    @property
    def platform(self) -> ServicePlatform:
        return self._platform

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    def config(self) -> ServiceConfig:
        return self._config

    def install(self) -> bool:
        self._state = ServiceState.INSTALLED
        logger.info("service_installed", platform=self._platform.value)
        return True

    def uninstall(self) -> bool:
        if self._state == ServiceState.NOT_INSTALLED:
            return False
        self._state = ServiceState.NOT_INSTALLED
        return True

    def start(self) -> bool:
        if self._state not in (ServiceState.INSTALLED, ServiceState.STOPPED):
            return False
        self._state = ServiceState.RUNNING
        logger.info("service_started")
        return True

    def stop(self) -> bool:
        if self._state != ServiceState.RUNNING:
            return False
        self._state = ServiceState.STOPPED
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def generate_launchd_plist(self) -> str:
        """Generate macOS launchd plist."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vaultbot.{self._config.name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{self._config.binary_path or "vaultbot"}</string>
        <string>run</string>
    </array>
    <key>KeepAlive</key>
    <{"true" if self._config.auto_restart else "false"}/>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""

    def generate_systemd_unit(self) -> str:
        """Generate Linux systemd unit file."""
        return f"""[Unit]
Description={self._config.description}
After=network.target

[Service]
Type=simple
ExecStart={self._config.binary_path or "vaultbot"} run
Restart={"always" if self._config.auto_restart else "no"}
WorkingDirectory={self._config.working_dir or "~"}

[Install]
WantedBy=multi-user.target
"""
