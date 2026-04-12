"""Plugin activation/deactivation lifecycle management."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class PluginState(str, Enum):
    INSTALLED = "installed"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass(slots=True)
class PluginLifecycleInfo:
    name: str
    state: PluginState = PluginState.INSTALLED
    activated_at: float = 0.0
    deactivated_at: float = 0.0
    error: str = ""
    activation_count: int = 0


class PluginLifecycleManager:
    """Manages plugin activation/deactivation lifecycle."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginLifecycleInfo] = {}

    def install(self, name: str) -> PluginLifecycleInfo:
        info = PluginLifecycleInfo(name=name)
        self._plugins[name] = info
        return info

    def activate(self, name: str) -> bool:
        info = self._plugins.get(name)
        if not info or info.state in (PluginState.ACTIVE, PluginState.ACTIVATING):
            return False
        info.state = PluginState.ACTIVATING
        info.state = PluginState.ACTIVE
        info.activated_at = time.time()
        info.activation_count += 1
        logger.info("plugin_activated", name=name)
        return True

    def deactivate(self, name: str) -> bool:
        info = self._plugins.get(name)
        if not info or info.state != PluginState.ACTIVE:
            return False
        info.state = PluginState.DEACTIVATING
        info.state = PluginState.INACTIVE
        info.deactivated_at = time.time()
        return True

    def get_state(self, name: str) -> PluginState | None:
        info = self._plugins.get(name)
        return info.state if info else None

    def list_active(self) -> list[PluginLifecycleInfo]:
        return [p for p in self._plugins.values() if p.state == PluginState.ACTIVE]

    def uninstall(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False
