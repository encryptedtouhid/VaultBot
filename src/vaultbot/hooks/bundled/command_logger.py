"""Command logging hook."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CommandLogEntry:
    command: str
    user_id: str = ""
    timestamp: float = field(default_factory=time.time)


class CommandLoggerHook:
    """Logs all commands for audit purposes."""

    def __init__(self) -> None:
        self._log: list[CommandLogEntry] = []

    async def on_command(self, command: str = "", user_id: str = "", **kwargs: object) -> None:
        entry = CommandLogEntry(command=command, user_id=user_id)
        self._log.append(entry)
        logger.info("command_logged", command=command, user_id=user_id)

    def get_log(self, limit: int = 50) -> list[CommandLogEntry]:
        return self._log[-limit:]

    @property
    def log_count(self) -> int:
        return len(self._log)
