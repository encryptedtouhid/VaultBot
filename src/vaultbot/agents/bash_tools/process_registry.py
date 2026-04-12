"""Background process tracking and job control."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ProcessMode(str, Enum):
    FOREGROUND = "foreground"
    BACKGROUND = "background"


class JobState(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class TrackedProcess:
    job_id: str
    command: list[str]
    mode: ProcessMode = ProcessMode.FOREGROUND
    state: JobState = JobState.RUNNING
    pid: int = 0
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    exit_code: int = -1
    output: str = ""


class ProcessRegistry:
    """Tracks background processes and manages job control."""

    def __init__(self) -> None:
        self._jobs: dict[str, TrackedProcess] = {}
        self._counter = 0

    def register(
        self, command: list[str], mode: ProcessMode = ProcessMode.FOREGROUND
    ) -> TrackedProcess:
        self._counter += 1
        job = TrackedProcess(
            job_id=f"job_{self._counter}",
            command=command,
            mode=mode,
        )
        self._jobs[job.job_id] = job
        return job

    def complete(self, job_id: str, exit_code: int = 0, output: str = "") -> bool:
        job = self._jobs.get(job_id)
        if not job or job.state != JobState.RUNNING:
            return False
        job.state = JobState.COMPLETED if exit_code == 0 else JobState.FAILED
        job.exit_code = exit_code
        job.output = output
        job.finished_at = time.time()
        return True

    def stop(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.state != JobState.RUNNING:
            return False
        job.state = JobState.STOPPED
        job.finished_at = time.time()
        return True

    def get(self, job_id: str) -> TrackedProcess | None:
        return self._jobs.get(job_id)

    def list_running(self) -> list[TrackedProcess]:
        return [j for j in self._jobs.values() if j.state == JobState.RUNNING]

    def list_background(self) -> list[TrackedProcess]:
        return [
            j
            for j in self._jobs.values()
            if j.mode == ProcessMode.BACKGROUND and j.state == JobState.RUNNING
        ]

    def cleanup_finished(self) -> int:
        finished = [
            jid
            for jid, j in self._jobs.items()
            if j.state in (JobState.COMPLETED, JobState.FAILED, JobState.STOPPED)
        ]
        for jid in finished:
            del self._jobs[jid]
        return len(finished)

    @property
    def job_count(self) -> int:
        return len(self._jobs)
