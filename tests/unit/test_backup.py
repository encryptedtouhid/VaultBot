"""Unit tests for backup and restore system."""

from __future__ import annotations

import pytest

from vaultbot.backup.manager import (
    BackupManager,
    BackupState,
    BackupStorage,
    InMemoryBackupStorage,
)


class TestInMemoryBackupStorage:
    def test_is_backup_storage(self) -> None:
        assert isinstance(InMemoryBackupStorage(), BackupStorage)

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self) -> None:
        store = InMemoryBackupStorage()
        await store.store("b1", b"data")
        assert await store.retrieve("b1") == b"data"

    @pytest.mark.asyncio
    async def test_retrieve_missing_raises(self) -> None:
        store = InMemoryBackupStorage()
        with pytest.raises(KeyError):
            await store.retrieve("nope")

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        store = InMemoryBackupStorage()
        await store.store("b1", b"data")
        assert await store.delete("b1") is True
        assert await store.delete("b1") is False

    @pytest.mark.asyncio
    async def test_list_backups(self) -> None:
        store = InMemoryBackupStorage()
        await store.store("b1", b"a")
        await store.store("b2", b"b")
        assert len(await store.list_backups()) == 2


class TestBackupManager:
    @pytest.mark.asyncio
    async def test_create_backup(self) -> None:
        mgr = BackupManager(InMemoryBackupStorage())
        meta = await mgr.create_backup("test", b"backup_data", ["config", "memory"])
        assert meta.state == BackupState.COMPLETED
        assert meta.size_bytes == len(b"backup_data")
        assert mgr.backup_count == 1

    @pytest.mark.asyncio
    async def test_restore_backup(self) -> None:
        mgr = BackupManager(InMemoryBackupStorage())
        meta = await mgr.create_backup("test", b"my_data")
        data = await mgr.restore_backup(meta.backup_id)
        assert data == b"my_data"

    @pytest.mark.asyncio
    async def test_restore_missing_raises(self) -> None:
        mgr = BackupManager(InMemoryBackupStorage())
        with pytest.raises(KeyError):
            await mgr.restore_backup("nope")

    @pytest.mark.asyncio
    async def test_list_backups(self) -> None:
        mgr = BackupManager(InMemoryBackupStorage())
        await mgr.create_backup("a", b"data1")
        await mgr.create_backup("b", b"data2")
        backups = mgr.list_backups()
        assert len(backups) == 2

    @pytest.mark.asyncio
    async def test_delete_backup(self) -> None:
        mgr = BackupManager(InMemoryBackupStorage())
        meta = await mgr.create_backup("test", b"data")
        assert await mgr.delete_backup(meta.backup_id) is True
        assert mgr.backup_count == 0

    @pytest.mark.asyncio
    async def test_prune(self) -> None:
        mgr = BackupManager(InMemoryBackupStorage(), max_backups=2)
        await mgr.create_backup("a", b"1")
        await mgr.create_backup("b", b"2")
        await mgr.create_backup("c", b"3")
        assert mgr.backup_count == 2
