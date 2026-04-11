"""Plugin discovery, verification, and loading.

Handles the full lifecycle of loading a plugin:
1. Discover plugin directory and manifest
2. Verify signature against trust store
3. Register in the local registry
4. Prepare for sandboxed execution
"""

from __future__ import annotations

import json
from pathlib import Path

from vaultbot.plugins.base import PluginManifest
from vaultbot.plugins.registry import PluginEntry, PluginRegistry
from vaultbot.plugins.signer import PluginVerifier
from vaultbot.security.audit import AuditLogger, EventType
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_MANIFEST_FILENAME = "vaultbot_plugin.json"


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""


class PluginLoader:
    """Discovers, verifies, and loads plugins into the registry."""

    def __init__(
        self,
        registry: PluginRegistry,
        verifier: PluginVerifier,
        audit: AuditLogger,
    ) -> None:
        self._registry = registry
        self._verifier = verifier
        self._audit = audit

    def load_plugin(self, plugin_dir: Path) -> PluginEntry:
        """Load a plugin from a directory.

        Verifies the signature and manifest before registering.

        Args:
            plugin_dir: Path to the plugin directory.

        Returns:
            The registered PluginEntry.

        Raises:
            PluginLoadError: If the plugin fails verification.
        """
        plugin_dir = plugin_dir.resolve()

        # 1. Read manifest
        manifest = self._read_manifest(plugin_dir)

        # 2. Verify signature
        signature = self._verifier.verify_plugin(plugin_dir)
        if signature is None:
            self._audit.log_action(
                event_type=EventType.PLUGIN_REJECTED,
                action_name=manifest.name,
                severity="high",
                reason="signature_verification_failed",
            )
            raise PluginLoadError(
                f"Plugin '{manifest.name}' failed signature verification. "
                "Unsigned or untrusted plugins cannot be loaded."
            )

        # 3. Find the main module
        module_path = self._find_main_module(plugin_dir, manifest.name)

        # 4. Register
        entry = PluginEntry(
            manifest=manifest,
            plugin_dir=plugin_dir,
            module_path=module_path,
        )
        self._registry.register(entry)

        self._audit.log_action(
            event_type=EventType.PLUGIN_LOADED,
            action_name=manifest.name,
            severity="info",
            version=manifest.version,
        )

        return entry

    def load_all_from_directory(self, plugins_dir: Path) -> list[PluginEntry]:
        """Load all valid plugins from a directory of plugin directories.

        Skips plugins that fail verification (logs warnings but doesn't raise).
        """
        loaded: list[PluginEntry] = []

        if not plugins_dir.exists():
            return loaded

        for item in sorted(plugins_dir.iterdir()):
            if not item.is_dir():
                continue
            manifest_path = item / _MANIFEST_FILENAME
            if not manifest_path.exists():
                continue

            try:
                entry = self.load_plugin(item)
                loaded.append(entry)
            except PluginLoadError as e:
                logger.warning("plugin_load_skipped", path=str(item), error=str(e))

        return loaded

    @staticmethod
    def _read_manifest(plugin_dir: Path) -> PluginManifest:
        """Read and validate the plugin manifest."""
        manifest_path = plugin_dir / _MANIFEST_FILENAME
        if not manifest_path.exists():
            raise PluginLoadError(
                f"No manifest file found at {manifest_path}. "
                f"Plugins must include a {_MANIFEST_FILENAME} file."
            )

        try:
            data = json.loads(manifest_path.read_text())
            return PluginManifest.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise PluginLoadError(f"Invalid manifest in {manifest_path}: {e}") from e

    @staticmethod
    def _find_main_module(plugin_dir: Path, plugin_name: str) -> Path:
        """Find the main Python module for the plugin."""
        # Try common conventions
        candidates = [
            plugin_dir / "plugin.py",
            plugin_dir / f"{plugin_name}.py",
            plugin_dir / "__init__.py",
            plugin_dir / "main.py",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Fall back to first .py file
        py_files = list(plugin_dir.glob("*.py"))
        if py_files:
            return py_files[0]

        raise PluginLoadError(
            f"No Python module found in {plugin_dir}. "
            "Plugins must contain at least one .py file."
        )
