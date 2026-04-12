"""ACP background task lifecycle with progress tracking."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ACPTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    session_id: str = ""
    description: str = ""
    state: TaskState = TaskState.PENDING
    progress: float = 0.0
    result: str = ""
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0
    timeout_seconds: float = 300.0


class ACPTaskExecutor:
    """Manages background task lifecycle within ACP sessions."""

    def __init__(self) -> None:
        self._tasks: dict[str, ACPTask] = {}

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def create_task(
        self, session_id: str, description: str = "", timeout: float = 300.0
    ) -> ACPTask:
        task = ACPTask(
            session_id=session_id,
            description=description,
            timeout_seconds=timeout,
        )
        self._tasks[task.task_id] = task
        logger.info("acp_task_created", task_id=task.task_id, session=session_id)
        return task

    def start_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.PENDING:
            return False
        task.state = TaskState.RUNNING
        task.started_at = time.time()
        return True

    def update_progress(self, task_id: str, progress: float) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.RUNNING:
            return False
        task.progress = min(max(progress, 0.0), 1.0)
        return True

    def complete_task(self, task_id: str, result: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.RUNNING:
            return False
        task.state = TaskState.COMPLETED
        task.result = result
        task.progress = 1.0
        task.finished_at = time.time()
        return True

    def fail_task(self, task_id: str, error: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.RUNNING:
            return False
        task.state = TaskState.FAILED
        task.error = error
        task.finished_at = time.time()
        return True

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.state in (TaskState.COMPLETED, TaskState.FAILED):
            return False
        task.state = TaskState.CANCELLED
        task.finished_at = time.time()
        return True

    def get_task(self, task_id: str) -> ACPTask | None:
        return self._tasks.get(task_id)

    def get_session_tasks(self, session_id: str) -> list[ACPTask]:
        return [t for t in self._tasks.values() if t.session_id == session_id]

    def check_timeouts(self) -> int:
        """Mark timed-out tasks. Returns count timed out."""
        now = time.time()
        count = 0
        for task in self._tasks.values():
            if task.state == TaskState.RUNNING:
                if (now - task.started_at) >= task.timeout_seconds:
                    task.state = TaskState.TIMED_OUT
                    task.finished_at = now
                    count += 1
        return count
