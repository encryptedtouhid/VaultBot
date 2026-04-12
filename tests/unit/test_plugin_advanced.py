"""Unit tests for enterprise plugin system."""

from __future__ import annotations

from vaultbot.plugins.command_registry import PluginCommand, PluginCommandRegistry
from vaultbot.plugins.lifecycle import PluginLifecycleManager, PluginState
from vaultbot.plugins.manifest import ManifestRegistry, PluginManifest


class TestPluginCommandRegistry:
    def test_register_and_match(self) -> None:
        reg = PluginCommandRegistry()
        reg.register(PluginCommand(name="weather", plugin_name="weather_plugin"))
        cmd = reg.match("/weather London")
        assert cmd is not None
        assert cmd.plugin_name == "weather_plugin"

    def test_match_non_command(self) -> None:
        reg = PluginCommandRegistry()
        assert reg.match("just text") is None

    def test_match_unknown(self) -> None:
        reg = PluginCommandRegistry()
        assert reg.match("/unknown") is None

    def test_unregister(self) -> None:
        reg = PluginCommandRegistry()
        reg.register(PluginCommand(name="test", plugin_name="p"))
        assert reg.unregister("test") is True
        assert reg.command_count == 0

    def test_list_by_plugin(self) -> None:
        reg = PluginCommandRegistry()
        reg.register(PluginCommand(name="a", plugin_name="p1"))
        reg.register(PluginCommand(name="b", plugin_name="p2"))
        assert len(reg.list_commands("p1")) == 1


class TestManifestRegistry:
    def test_register_and_get(self) -> None:
        reg = ManifestRegistry()
        reg.register(PluginManifest(name="weather", version="1.0.0"))
        assert reg.get("weather") is not None
        assert reg.plugin_count == 1

    def test_has_capability(self) -> None:
        reg = ManifestRegistry()
        reg.register(PluginManifest(name="img", capabilities=["image_gen"]))
        assert reg.has_capability("img", "image_gen") is True
        assert reg.has_capability("img", "audio") is False

    def test_find_by_capability(self) -> None:
        reg = ManifestRegistry()
        reg.register(PluginManifest(name="a", capabilities=["search"]))
        reg.register(PluginManifest(name="b", capabilities=["chat"]))
        assert len(reg.find_by_capability("search")) == 1


class TestPluginLifecycle:
    def test_install(self) -> None:
        mgr = PluginLifecycleManager()
        info = mgr.install("test")
        assert info.state == PluginState.INSTALLED

    def test_activate(self) -> None:
        mgr = PluginLifecycleManager()
        mgr.install("test")
        assert mgr.activate("test") is True
        assert mgr.get_state("test") == PluginState.ACTIVE

    def test_deactivate(self) -> None:
        mgr = PluginLifecycleManager()
        mgr.install("test")
        mgr.activate("test")
        assert mgr.deactivate("test") is True
        assert mgr.get_state("test") == PluginState.INACTIVE

    def test_list_active(self) -> None:
        mgr = PluginLifecycleManager()
        mgr.install("a")
        mgr.install("b")
        mgr.activate("a")
        assert len(mgr.list_active()) == 1

    def test_uninstall(self) -> None:
        mgr = PluginLifecycleManager()
        mgr.install("test")
        assert mgr.uninstall("test") is True
        assert mgr.get_state("test") is None
