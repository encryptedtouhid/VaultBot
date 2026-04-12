"""Backup manager for creating, restoring, listing, and pruning backups."""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class BackupState(str, Enum):
    CREATING = "creating"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORING = "restoring"


@dataclass(slots=True)
class BackupMetadata:
    backup_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    state: BackupState = BackupState.CREATING
    created_at: float = field(default_factory=time.time)
    size_bytes: int = 0
    checksum: str = ""
    components: list[str] = field(default_factory=list)


@runtime_checkable
class BackupStorage(Protocol):
    async def store(self, backup_id: str, data: bytes) -> None: ...
    async def retrieve(self, backup_id: str) -> bytes: ...
    async def delete(self, backup_id: str) -> bool: ...
    async def list_backups(self) -> list[str]: ...


class InMemoryBackupStorage:
    """In-memory backup storage for testing."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def store(self, backup_id: str, data: bytes) -> None:
        self._store[backup_id] = data

    async def retrieve(self, backup_id: str) -> bytes:
        if backup_id not in self._store:
            raise KeyError(f"Backup {backup_id} not found")
        return self._store[backup_id]

    async def delete(self, backup_id: str) -> bool:
        if backup_id in self._store:
            del self._store[backup_id]
            return True
        return False

    async def list_backups(self) -> list[str]:
        return list(self._store.keys())


class BackupManager:
    """Manages backup creation, restoration, and pruning."""

    def __init__(self, storage: BackupStorage, max_backups: int = 10) -> None:
        self._storage = storage
        self._max_backups = max_backups
        self._metadata: dict[str, BackupMetadata] = {}

    @property
    def backup_count(self) -> int:
        return len(self._metadata)

    async def create_backup(
        self, name: str, data: bytes, components: list[str] | None = None
    ) -> BackupMetadata:
        meta = BackupMetadata(
            name=name,
            size_bytes=len(data),
            checksum=hashlib.sha256(data).hexdigest()[:16],
            components=components or [],
        )
        await self._storage.store(meta.backup_id, data)
        meta.state = BackupState.COMPLETED
        self._metadata[meta.backup_id] = meta
        logger.info("backup_created", id=meta.backup_id, size=meta.size_bytes)
        await self._prune()
        return meta

    async def restore_backup(self, backup_id: str) -> bytes:
        meta = self._metadata.get(backup_id)
        if not meta:
            raise KeyError(f"Backup {backup_id} not found")
        meta.state = BackupState.RESTORING
        data = await self._storage.retrieve(backup_id)
        logger.info("backup_restored", id=backup_id)
        return data

    def list_backups(self) -> list[BackupMetadata]:
        return sorted(self._metadata.values(), key=lambda m: m.created_at, reverse=True)

    async def delete_backup(self, backup_id: str) -> bool:
        if backup_id in self._metadata:
            await self._storage.delete(backup_id)
            del self._metadata[backup_id]
            return True
        return False

    async def _prune(self) -> None:
        while len(self._metadata) > self._max_backups:
            oldest = min(self._metadata.values(), key=lambda m: m.created_at)
            await self.delete_backup(oldest.backup_id)
