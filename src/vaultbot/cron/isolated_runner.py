"""Isolated agent runner for cron jobs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class RunnerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class IsolatedRun:
    run_id: str = ""
    job_id: str = ""
    agent_id: str = ""
    model: str = ""
    state: RunnerState = RunnerState.IDLE
    started_at: float = 0.0
    finished_at: float = 0.0
    output: str = ""
    error: str = ""


class IsolatedRunner:
    """Runs cron jobs in isolated agent contexts."""

    def __init__(self) -> None:
        self._runs: dict[str, IsolatedRun] = {}
        self._counter = 0

    @property
    def run_count(self) -> int:
        return len(self._runs)

    def create_run(self, job_id: str, agent_id: str = "", model: str = "") -> IsolatedRun:
        self._counter += 1
        run = IsolatedRun(
            run_id=f"run_{self._counter}",
            job_id=job_id,
            agent_id=agent_id,
            model=model,
        )
        self._runs[run.run_id] = run
        return run

    def start_run(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if not run or run.state != RunnerState.IDLE:
            return False
        run.state = RunnerState.RUNNING
        run.started_at = time.time()
        return True

    def complete_run(self, run_id: str, output: str = "") -> bool:
        run = self._runs.get(run_id)
        if not run or run.state != RunnerState.RUNNING:
            return False
        run.state = RunnerState.COMPLETED
        run.output = output
        run.finished_at = time.time()
        return True

    def fail_run(self, run_id: str, error: str = "") -> bool:
        run = self._runs.get(run_id)
        if not run or run.state != RunnerState.RUNNING:
            return False
        run.state = RunnerState.FAILED
        run.error = error
        run.finished_at = time.time()
        return True

    def get_run(self, run_id: str) -> IsolatedRun | None:
        return self._runs.get(run_id)

    def list_by_job(self, job_id: str) -> list[IsolatedRun]:
        return [r for r in self._runs.values() if r.job_id == job_id]
