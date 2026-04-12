"""Plugin manifest and bundling management."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Plugin manifest describing capabilities and metadata."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    entry_point: str = ""
    commands: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    config_schema: dict[str, object] = field(default_factory=dict)
    mcp_tools: list[str] = field(default_factory=list)


class ManifestRegistry:
    """Manages plugin manifests."""

    def __init__(self) -> None:
        self._manifests: dict[str, PluginManifest] = {}

    def register(self, manifest: PluginManifest) -> None:
        self._manifests[manifest.name] = manifest
        logger.info("manifest_registered", name=manifest.name, version=manifest.version)

    def get(self, name: str) -> PluginManifest | None:
        return self._manifests.get(name)

    def list_manifests(self) -> list[PluginManifest]:
        return list(self._manifests.values())

    def has_capability(self, name: str, capability: str) -> bool:
        manifest = self._manifests.get(name)
        return manifest is not None and capability in manifest.capabilities

    def find_by_capability(self, capability: str) -> list[PluginManifest]:
        return [m for m in self._manifests.values() if capability in m.capabilities]

    @property
    def plugin_count(self) -> int:
        return len(self._manifests)
