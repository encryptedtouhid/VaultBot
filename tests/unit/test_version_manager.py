"""Unit tests for plugin version manager."""

from __future__ import annotations

from vaultbot.plugins.version_manager import (
    PluginVersionManager,
    is_newer,
    parse_version,
)


class TestVersionParsing:
    def test_semver(self) -> None:
        assert parse_version("1.2.3") == (1, 2, 3)

    def test_simple(self) -> None:
        assert parse_version("2") == (2,)

    def test_with_prefix(self) -> None:
        assert parse_version("v1.0.0") == (1, 0, 0)

    def test_empty(self) -> None:
        assert parse_version("") == (0,)

    def test_is_newer_true(self) -> None:
        assert is_newer("1.0.0", "1.0.1") is True
        assert is_newer("1.0.0", "2.0.0") is True

    def test_is_newer_false(self) -> None:
        assert is_newer("1.0.1", "1.0.0") is False
        assert is_newer("1.0.0", "1.0.0") is False


class TestPluginVersionManager:
    def test_install(self) -> None:
        mgr = PluginVersionManager()
        plugin = mgr.install("weather", "1.0.0")
        assert plugin.name == "weather"
        assert plugin.version == "1.0.0"
        assert mgr.count == 1

    def test_uninstall(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("weather", "1.0.0")
        assert mgr.uninstall("weather") is True
        assert mgr.count == 0

    def test_uninstall_nonexistent(self) -> None:
        mgr = PluginVersionManager()
        assert mgr.uninstall("nope") is False

    def test_get(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("calc", "2.0.0")
        plugin = mgr.get("calc")
        assert plugin is not None
        assert plugin.version == "2.0.0"

    def test_get_nonexistent(self) -> None:
        mgr = PluginVersionManager()
        assert mgr.get("nope") is None

    def test_list_installed(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("a", "1.0")
        mgr.install("b", "2.0")
        assert len(mgr.list_installed()) == 2

    def test_pin_version(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("calc", "1.0.0")
        assert mgr.pin_version("calc") is True
        assert mgr.get("calc").pinned is True

    def test_unpin_version(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("calc", "1.0.0")
        mgr.pin_version("calc")
        mgr.unpin_version("calc")
        assert mgr.get("calc").pinned is False

    def test_pin_nonexistent(self) -> None:
        mgr = PluginVersionManager()
        assert mgr.pin_version("nope") is False

    def test_check_updates(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("a", "1.0.0")
        mgr.install("b", "2.0.0")

        updates = mgr.check_updates({"a": "1.1.0", "b": "2.0.0"})
        assert len(updates) == 1
        assert updates[0].name == "a"
        assert updates[0].latest_version == "1.1.0"

    def test_check_updates_pinned_skipped(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("a", "1.0.0")
        mgr.pin_version("a")

        updates = mgr.check_updates({"a": "2.0.0"})
        assert len(updates) == 0

    def test_auto_update_plugins(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("a", "1.0", auto_update=True)
        mgr.install("b", "1.0", auto_update=False)
        mgr.install("c", "1.0", auto_update=True)
        mgr.pin_version("c")

        auto = mgr.get_auto_update_plugins()
        assert len(auto) == 1
        assert auto[0].name == "a"

    def test_reinstall_overwrites(self) -> None:
        mgr = PluginVersionManager()
        mgr.install("a", "1.0.0")
        mgr.install("a", "2.0.0")
        assert mgr.get("a").version == "2.0.0"
        assert mgr.count == 1
