"""Plugin slash command registration and matching."""

from __future__ import annotations

from dataclasses import dataclass

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PluginCommand:
    """A slash command registered by a plugin."""

    name: str
    plugin_name: str
    description: str = ""
    usage: str = ""
    bypass_llm: bool = True


class PluginCommandRegistry:
    """Registry for plugin-provided slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, PluginCommand] = {}

    def register(self, command: PluginCommand) -> None:
        self._commands[command.name] = command
        logger.info("plugin_command_registered", name=command.name, plugin=command.plugin_name)

    def unregister(self, name: str) -> bool:
        if name in self._commands:
            del self._commands[name]
            return True
        return False

    def match(self, text: str) -> PluginCommand | None:
        """Match text against registered slash commands."""
        if not text.startswith("/"):
            return None
        cmd_name = text.split()[0][1:]
        return self._commands.get(cmd_name)

    def list_commands(self, plugin_name: str = "") -> list[PluginCommand]:
        if plugin_name:
            return [c for c in self._commands.values() if c.plugin_name == plugin_name]
        return list(self._commands.values())

    @property
    def command_count(self) -> int:
        return len(self._commands)
