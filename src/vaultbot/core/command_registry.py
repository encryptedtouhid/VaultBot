"""Command registry for slash commands and auto-complete."""

from __future__ import annotations

import re
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class CommandScope(str, Enum):
    TEXT = "text"
    NATIVE = "native"
    BOTH = "both"


@dataclass(frozen=True, slots=True)
class CommandArg:
    name: str
    required: bool = True
    description: str = ""
    default: str = ""


@dataclass(frozen=True, slots=True)
class CommandDefinition:
    name: str
    description: str = ""
    scope: CommandScope = CommandScope.BOTH
    args: list[CommandArg] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)


CommandHandler = Callable[..., Coroutine[Any, Any, str]]


class CommandRegistry:
    """Registry for slash commands that bypass the LLM."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandDefinition] = {}
        self._handlers: dict[str, CommandHandler] = {}
        self._alias_map: dict[str, str] = {}

    def register(self, definition: CommandDefinition, handler: CommandHandler) -> None:
        self._commands[definition.name] = definition
        self._handlers[definition.name] = handler
        for alias in definition.aliases:
            self._alias_map[alias] = definition.name
        logger.info("command_registered", name=definition.name)

    def resolve(self, name: str) -> CommandDefinition | None:
        if name in self._commands:
            return self._commands[name]
        canonical = self._alias_map.get(name)
        if canonical:
            return self._commands.get(canonical)
        return None

    def parse_command(self, text: str) -> tuple[str, list[str]] | None:
        """Parse a slash command from text. Returns (name, args) or None."""
        match = re.match(r"^/(\w+)\s*(.*)", text.strip())
        if not match:
            return None
        name = match.group(1)
        args_str = match.group(2).strip()
        args = args_str.split() if args_str else []
        return name, args

    async def execute(self, text: str) -> str | None:
        """Parse and execute a slash command. Returns response or None if not a command."""
        parsed = self.parse_command(text)
        if not parsed:
            return None
        name, args = parsed
        defn = self.resolve(name)
        if not defn:
            return None
        handler = self._handlers.get(defn.name)
        if not handler:
            return None
        return await handler(*args)

    def autocomplete(self, prefix: str) -> list[str]:
        """Return command names matching a prefix."""
        prefix = prefix.lstrip("/").lower()
        matches = []
        for name in self._commands:
            if name.lower().startswith(prefix):
                matches.append(f"/{name}")
        for alias in self._alias_map:
            if alias.lower().startswith(prefix):
                matches.append(f"/{alias}")
        return sorted(set(matches))

    def list_commands(self) -> list[CommandDefinition]:
        return list(self._commands.values())
