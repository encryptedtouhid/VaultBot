"""Plugin version management and update checking.

Tracks installed plugin versions, checks for available updates,
and manages version pinning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class InstalledPlugin:
    """Tracks an installed plugin and its version."""
    name: str
    version: str
    installed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    pinned: bool = False
    auto_update: bool = False
    source: str = "marketplace"  # marketplace, local, git


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    """Information about an available update."""
    name: str
    current_version: str
    latest_version: str
    changelog: str = ""


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a semver-like version string into comparable tuple."""
    parts = re.findall(r"\d+", version)
    return tuple(int(p) for p in parts) if parts else (0,)


def is_newer(current: str, candidate: str) -> bool:
    """Check if candidate version is newer than current."""
    return parse_version(candidate) > parse_version(current)


class PluginVersionManager:
    """Manages installed plugin versions and updates."""

    def __init__(self) -> None:
        self._installed: dict[str, InstalledPlugin] = {}

    def install(
        self,
        name: str,
        version: str,
        *,
        source: str = "marketplace",
        auto_update: bool = False,
    ) -> InstalledPlugin:
        """Record a plugin installation."""
        plugin = InstalledPlugin(
            name=name,
            version=version,
            source=source,
            auto_update=auto_update,
        )
        self._installed[name] = plugin
        logger.info("plugin_installed", name=name, version=version)
        return plugin

    def uninstall(self, name: str) -> bool:
        """Remove a plugin from tracking."""
        if name in self._installed:
            del self._installed[name]
            logger.info("plugin_uninstalled", name=name)
            return True
        return False

    def get(self, name: str) -> InstalledPlugin | None:
        """Get installed plugin info."""
        return self._installed.get(name)

    def list_installed(self) -> list[InstalledPlugin]:
        """List all installed plugins."""
        return list(self._installed.values())

    def pin_version(self, name: str) -> bool:
        """Pin a plugin to its current version (prevent auto-updates)."""
        plugin = self._installed.get(name)
        if plugin:
            plugin.pinned = True
            return True
        return False

    def unpin_version(self, name: str) -> bool:
        """Unpin a plugin version."""
        plugin = self._installed.get(name)
        if plugin:
            plugin.pinned = False
            return True
        return False

    def check_updates(
        self, available_versions: dict[str, str]
    ) -> list[UpdateInfo]:
        """Check which installed plugins have available updates.

        Parameters
        ----------
        available_versions:
            Mapping of plugin name -> latest available version.

        Returns list of plugins with newer versions available.
        """
        updates: list[UpdateInfo] = []
        for name, plugin in self._installed.items():
            if plugin.pinned:
                continue
            latest = available_versions.get(name)
            if latest and is_newer(plugin.version, latest):
                updates.append(UpdateInfo(
                    name=name,
                    current_version=plugin.version,
                    latest_version=latest,
                ))
        return updates

    def get_auto_update_plugins(self) -> list[InstalledPlugin]:
        """Get plugins with auto-update enabled (and not pinned)."""
        return [
            p for p in self._installed.values()
            if p.auto_update and not p.pinned
        ]

    @property
    def count(self) -> int:
        return len(self._installed)
