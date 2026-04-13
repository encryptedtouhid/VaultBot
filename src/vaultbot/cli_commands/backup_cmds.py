"""Backup management CLI commands."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BackupInfo:
    backup_id: str
    name: str
    size_bytes: int = 0
    created_at: str = ""
    components: list[str] = field(default_factory=list)


class BackupCommands:
    """CLI commands for backup management."""

    def __init__(self) -> None:
        self._backups: dict[str, BackupInfo] = {}
        self._counter = 0

    def create(self, name: str, components: list[str] | None = None) -> BackupInfo:
        self._counter += 1
        info = BackupInfo(
            backup_id=f"bak_{self._counter}",
            name=name,
            components=components or ["config", "memory"],
        )
        self._backups[info.backup_id] = info
        return info

    def restore(self, backup_id: str) -> bool:
        return backup_id in self._backups

    def list_backups(self) -> list[BackupInfo]:
        return list(self._backups.values())

    def delete(self, backup_id: str) -> bool:
        if backup_id in self._backups:
            del self._backups[backup_id]
            return True
        return False
