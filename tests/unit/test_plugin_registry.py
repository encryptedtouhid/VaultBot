"""Tests for plugin registry."""

import tempfile
from pathlib import Path

from vaultbot.plugins.base import PluginManifest
from vaultbot.plugins.registry import PluginEntry, PluginRegistry


def _make_entry(name: str = "test-plugin") -> PluginEntry:
    return PluginEntry(
        manifest=PluginManifest(
            name=name,
            version="1.0.0",
            description="A test plugin",
            author="tester",
        ),
        plugin_dir=Path("/fake/path"),
        module_path=Path("/fake/path/plugin.py"),
    )


def test_register_and_get() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = PluginRegistry(registry_dir=Path(tmpdir))
        entry = _make_entry()
        registry.register(entry)

        result = registry.get("test-plugin")
        assert result is not None
        assert result.manifest.name == "test-plugin"


def test_list_plugins() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = PluginRegistry(registry_dir=Path(tmpdir))
        registry.register(_make_entry("plugin-a"))
        registry.register(_make_entry("plugin-b"))
        assert len(registry.list_plugins()) == 2


def test_unregister() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = PluginRegistry(registry_dir=Path(tmpdir))
        registry.register(_make_entry())
        entry = registry.unregister("test-plugin")
        assert entry is not None
        assert registry.get("test-plugin") is None


def test_enable_disable() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = PluginRegistry(registry_dir=Path(tmpdir))
        registry.register(_make_entry())

        registry.disable("test-plugin")
        assert len(registry.list_enabled()) == 0

        registry.enable("test-plugin")
        assert len(registry.list_enabled()) == 1


def test_persistence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_dir = Path(tmpdir)

        # Register in one instance
        reg1 = PluginRegistry(registry_dir=registry_dir)
        reg1.register(_make_entry())

        # Load in a new instance
        reg2 = PluginRegistry(registry_dir=registry_dir)
        assert reg2.get("test-plugin") is not None


def test_entry_serialization() -> None:
    entry = _make_entry()
    data = entry.to_dict()
    restored = PluginEntry.from_dict(data)
    assert restored.manifest.name == entry.manifest.name
    assert restored.enabled == entry.enabled
