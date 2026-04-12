"""Unit tests for CLI command expansions."""

from __future__ import annotations

from vaultbot.cli_commands.config_cmds import ConfigCommands
from vaultbot.cli_commands.plugin_cmds import PluginCommands
from vaultbot.cli_commands.status_cmds import StatusCommands


class TestPluginCommands:
    def test_install_and_list(self) -> None:
        cmds = PluginCommands()
        cmds.install("calculator", "1.0")
        plugins = cmds.list_plugins()
        assert len(plugins) == 1
        assert plugins[0].name == "calculator"

    def test_uninstall(self) -> None:
        cmds = PluginCommands()
        cmds.install("test")
        assert cmds.uninstall("test") is True
        assert len(cmds.list_plugins()) == 0

    def test_enable_disable(self) -> None:
        cmds = PluginCommands()
        cmds.install("test")
        assert cmds.disable("test") is True
        assert not cmds.list_plugins()[0].enabled
        assert cmds.enable("test") is True
        assert cmds.list_plugins()[0].enabled


class TestConfigCommands:
    def test_list_keys(self) -> None:
        cmds = ConfigCommands()
        keys = cmds.list_keys()
        assert "log_level" in keys

    def test_get_default(self) -> None:
        cmds = ConfigCommands()
        assert cmds.get("missing", "default") == "default"

    def test_set_value(self) -> None:
        cmds = ConfigCommands()
        assert cmds.set_value("key", "value") is True

    def test_reset(self) -> None:
        cmds = ConfigCommands()
        assert cmds.reset("log_level") is True


class TestStatusCommands:
    def test_get_version(self) -> None:
        cmds = StatusCommands(version="1.0.0")
        assert cmds.get_version() == "1.0.0"

    def test_get_status(self) -> None:
        cmds = StatusCommands()
        status = cmds.get_status()
        assert status.python_version != ""

    def test_check_health(self) -> None:
        cmds = StatusCommands()
        health = cmds.check_health()
        assert "python_ok" in health

    def test_diagnostics(self) -> None:
        cmds = StatusCommands()
        diag = cmds.get_diagnostics()
        assert "python" in diag
