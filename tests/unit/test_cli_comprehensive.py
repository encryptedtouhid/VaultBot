"""Unit tests for comprehensive CLI commands."""

from __future__ import annotations

from vaultbot.cli_commands.agent_cmds import AgentCommands
from vaultbot.cli_commands.channel_cmds import ChannelCommands
from vaultbot.cli_commands.completion import (
    generate_bash_completion,
    generate_fish_completion,
    generate_zsh_completion,
)
from vaultbot.cli_commands.model_cmds import ModelCommands
from vaultbot.cli_commands.security_cmds import SecurityCommands


class TestAgentCommands:
    def test_create_and_list(self) -> None:
        cmds = AgentCommands()
        cmds.create("a1", "Agent 1", "gpt-4o")
        assert len(cmds.list_agents()) == 1

    def test_delete(self) -> None:
        cmds = AgentCommands()
        cmds.create("a1")
        assert cmds.delete("a1") is True
        assert len(cmds.list_agents()) == 0

    def test_get(self) -> None:
        cmds = AgentCommands()
        cmds.create("a1", "Test")
        assert cmds.get("a1") is not None
        assert cmds.get("nope") is None

    def test_bind(self) -> None:
        cmds = AgentCommands()
        cmds.create("a1")
        assert cmds.bind("a1", "general") is True
        assert cmds.bind("nope", "general") is False


class TestChannelCommands:
    def test_add_and_list(self) -> None:
        cmds = ChannelCommands()
        cmds.add("telegram")
        assert len(cmds.list_channels()) == 1

    def test_remove(self) -> None:
        cmds = ChannelCommands()
        cmds.add("telegram")
        assert cmds.remove("telegram") is True

    def test_enable_disable(self) -> None:
        cmds = ChannelCommands()
        cmds.add("telegram")
        assert cmds.disable("telegram") is True
        assert cmds.status("telegram").enabled is False
        assert cmds.enable("telegram") is True


class TestSecurityCommands:
    def test_run_audit(self) -> None:
        cmds = SecurityCommands()
        findings = cmds.run_audit()
        assert len(findings) > 0

    def test_format_findings(self) -> None:
        cmds = SecurityCommands()
        findings = cmds.run_audit()
        formatted = cmds.format_findings(findings)
        assert "INFO" in formatted

    def test_format_no_findings(self) -> None:
        cmds = SecurityCommands()
        assert cmds.format_findings([]) == "No findings"


class TestModelCommands:
    def test_add_and_list(self) -> None:
        cmds = ModelCommands()
        cmds.add_model("gpt-4o", "openai", 128000)
        assert len(cmds.list_models()) == 1

    def test_set_default(self) -> None:
        cmds = ModelCommands()
        cmds.add_model("gpt-4o")
        cmds.add_model("claude-3")
        assert cmds.set_default("claude-3") is True
        assert cmds.get_default() == "claude-3"


class TestCompletion:
    def test_bash(self) -> None:
        script = generate_bash_completion(["help", "status", "run"])
        assert "vaultbot" in script
        assert "help" in script

    def test_zsh(self) -> None:
        script = generate_zsh_completion(["help", "status"])
        assert "#compdef" in script
        assert "help" in script

    def test_fish(self) -> None:
        script = generate_fish_completion(["help", "status"])
        assert "complete" in script
        assert "help" in script
