"""Persistent job storage for cron scheduler."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vaultbot.cron.scheduler import CronJob
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class JobStore(Protocol):
    """Protocol for persistent job storage."""

    async def save_job(self, job: CronJob) -> None: ...
    async def load_job(self, job_id: str) -> CronJob | None: ...
    async def delete_job(self, job_id: str) -> bool: ...
    async def list_jobs(self) -> list[CronJob]: ...


class InMemoryJobStore:
    """In-memory job store for development/testing."""

    def __init__(self) -> None:
        self._store: dict[str, CronJob] = {}

    async def save_job(self, job: CronJob) -> None:
        self._store[job.id] = job

    async def load_job(self, job_id: str) -> CronJob | None:
        return self._store.get(job_id)

    async def delete_job(self, job_id: str) -> bool:
        if job_id in self._store:
            del self._store[job_id]
            return True
        return False

    async def list_jobs(self) -> list[CronJob]:
        return list(self._store.values())
