"""Process supervisor with lifecycle management."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ProcessState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


@dataclass(slots=True)
class SupervisedProcess:
    process_id: str
    args: list[str] = field(default_factory=list)
    state: ProcessState = ProcessState.PENDING
    pid: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0
    exit_code: int = -1


class ProcessSupervisor:
    """Supervises process lifecycle."""

    def __init__(self) -> None:
        self._processes: dict[str, SupervisedProcess] = {}
        self._counter = 0

    @property
    def process_count(self) -> int:
        return len(self._processes)

    def register(self, args: list[str]) -> SupervisedProcess:
        self._counter += 1
        pid = f"proc_{self._counter}"
        proc = SupervisedProcess(process_id=pid, args=args)
        self._processes[pid] = proc
        return proc

    def start(self, process_id: str) -> bool:
        proc = self._processes.get(process_id)
        if not proc or proc.state != ProcessState.PENDING:
            return False
        proc.state = ProcessState.RUNNING
        proc.started_at = time.time()
        return True

    def mark_completed(self, process_id: str, exit_code: int = 0) -> bool:
        proc = self._processes.get(process_id)
        if not proc or proc.state != ProcessState.RUNNING:
            return False
        proc.state = ProcessState.COMPLETED if exit_code == 0 else ProcessState.FAILED
        proc.exit_code = exit_code
        proc.finished_at = time.time()
        return True

    def kill(self, process_id: str) -> bool:
        proc = self._processes.get(process_id)
        if not proc or proc.state != ProcessState.RUNNING:
            return False
        proc.state = ProcessState.KILLED
        proc.finished_at = time.time()
        return True

    def get(self, process_id: str) -> SupervisedProcess | None:
        return self._processes.get(process_id)

    def list_running(self) -> list[SupervisedProcess]:
        return [p for p in self._processes.values() if p.state == ProcessState.RUNNING]

    def cleanup_finished(self) -> int:
        finished = [
            pid
            for pid, p in self._processes.items()
            if p.state in (ProcessState.COMPLETED, ProcessState.FAILED, ProcessState.KILLED)
        ]
        for pid in finished:
            del self._processes[pid]
        return len(finished)
