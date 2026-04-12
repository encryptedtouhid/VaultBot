"""Plugin management CLI commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PluginInfo:
    name: str
    version: str
    enabled: bool
    description: str = ""


class PluginCommands:
    """CLI commands for plugin management."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}

    def list_plugins(self) -> list[PluginInfo]:
        return list(self._plugins.values())

    def install(self, name: str, version: str = "latest") -> PluginInfo:
        info = PluginInfo(name=name, version=version, enabled=True)
        self._plugins[name] = info
        return info

    def uninstall(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    def enable(self, name: str) -> bool:
        if name in self._plugins:
            self._plugins[name] = PluginInfo(
                name=name,
                version=self._plugins[name].version,
                enabled=True,
                description=self._plugins[name].description,
            )
            return True
        return False

    def disable(self, name: str) -> bool:
        if name in self._plugins:
            self._plugins[name] = PluginInfo(
                name=name,
                version=self._plugins[name].version,
                enabled=False,
                description=self._plugins[name].description,
            )
            return True
        return False
