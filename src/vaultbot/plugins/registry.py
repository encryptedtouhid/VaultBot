"""Local plugin registry — tracks installed plugins and their metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vaultbot.plugins.base import PluginManifest
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_REGISTRY_DIR = Path.home() / ".vaultbot" / "plugins"
_REGISTRY_FILE = "registry.json"


@dataclass
class PluginEntry:
    """A single entry in the plugin registry."""

    manifest: PluginManifest
    plugin_dir: Path
    module_path: Path  # Path to the main .py file
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "plugin_dir": str(self.plugin_dir),
            "module_path": str(self.module_path),
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginEntry:
        return cls(
            manifest=PluginManifest.from_dict(data["manifest"]),
            plugin_dir=Path(data["plugin_dir"]),
            module_path=Path(data["module_path"]),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )


class PluginRegistry:
    """Manages the local registry of installed plugins."""

    def __init__(self, registry_dir: Path | None = None) -> None:
        self._registry_dir = registry_dir or _DEFAULT_REGISTRY_DIR
        self._registry_file = self._registry_dir / _REGISTRY_FILE
        self._plugins: dict[str, PluginEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load the registry from disk."""
        if not self._registry_file.exists():
            return
        try:
            data = json.loads(self._registry_file.read_text())
            for name, entry_data in data.items():
                self._plugins[name] = PluginEntry.from_dict(entry_data)
            logger.info("registry_loaded", plugin_count=len(self._plugins))
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("registry_load_error", error=str(e))

    def _save(self) -> None:
        """Persist the registry to disk."""
        self._registry_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        data = {name: entry.to_dict() for name, entry in self._plugins.items()}
        self._registry_file.write_text(json.dumps(data, indent=2))
        self._registry_file.chmod(0o600)

    def register(self, entry: PluginEntry) -> None:
        """Register a plugin in the registry."""
        self._plugins[entry.manifest.name] = entry
        self._save()
        logger.info(
            "plugin_registered",
            name=entry.manifest.name,
            version=entry.manifest.version,
        )

    def unregister(self, name: str) -> PluginEntry | None:
        """Remove a plugin from the registry."""
        entry = self._plugins.pop(name, None)
        if entry:
            self._save()
            logger.info("plugin_unregistered", name=name)
        return entry

    def get(self, name: str) -> PluginEntry | None:
        """Get a plugin entry by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginEntry]:
        """List all registered plugins."""
        return list(self._plugins.values())

    def list_enabled(self) -> list[PluginEntry]:
        """List only enabled plugins."""
        return [p for p in self._plugins.values() if p.enabled]

    def enable(self, name: str) -> bool:
        """Enable a plugin. Returns True if found."""
        entry = self._plugins.get(name)
        if entry:
            entry.enabled = True
            self._save()
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a plugin. Returns True if found."""
        entry = self._plugins.get(name)
        if entry:
            entry.enabled = False
            self._save()
            return True
        return False
