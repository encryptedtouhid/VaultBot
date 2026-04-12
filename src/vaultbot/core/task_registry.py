"""Persistent task registry with SQLite-compatible storage."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class RegisteredTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    owner_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: str = ""
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)


class TaskRegistry:
    """In-memory task registry (SQLite-compatible interface)."""

    def __init__(self) -> None:
        self._tasks: dict[str, RegisteredTask] = {}

    @property
    def count(self) -> int:
        return len(self._tasks)

    def create(self, name: str, owner_id: str = "", description: str = "") -> RegisteredTask:
        task = RegisteredTask(name=name, owner_id=owner_id, description=description)
        self._tasks[task.task_id] = task
        logger.info("task_registered", task_id=task.task_id, name=name)
        return task

    def get(self, task_id: str) -> RegisteredTask | None:
        return self._tasks.get(task_id)

    def start(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        return True

    def complete(self, task_id: str, result: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.progress = 1.0
        task.finished_at = time.time()
        return True

    def fail(self, task_id: str, error: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        task.status = TaskStatus.FAILED
        task.error = error
        task.finished_at = time.time()
        return True

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return False
        task.status = TaskStatus.CANCELLED
        task.finished_at = time.time()
        return True

    def list_by_owner(self, owner_id: str) -> list[RegisteredTask]:
        return [t for t in self._tasks.values() if t.owner_id == owner_id]

    def list_by_status(self, status: TaskStatus) -> list[RegisteredTask]:
        return [t for t in self._tasks.values() if t.status == status]

    def delete(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def cleanup_old(self, max_age_seconds: float = 86400) -> int:
        now = time.time()
        to_remove = [
            tid
            for tid, t in self._tasks.items()
            if t.finished_at > 0 and (now - t.finished_at) > max_age_seconds
        ]
        for tid in to_remove:
            del self._tasks[tid]
        return len(to_remove)
