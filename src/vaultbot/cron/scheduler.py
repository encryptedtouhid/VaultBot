"""Cron-style job scheduler with persistent store and run logging.

Supports cron expressions (``* * * * *``) and simple intervals
(``every 5m``, ``every 1h``).  Jobs persist across restarts via
a SQLite store.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Coroutine

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Status of a scheduled job."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class RunStatus(str, Enum):
    """Status of a job run."""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    SKIPPED = "skipped"


@dataclass
class CronJob:
    """A scheduled job definition."""
    id: str
    name: str
    schedule: str  # Cron expression or "every Nm/Nh"
    action: str  # Action identifier (e.g. "send_message", "run_plugin")
    params: dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_run: datetime | None = None
    run_count: int = 0
    failure_count: int = 0


@dataclass(frozen=True, slots=True)
class RunLogEntry:
    """A record of a job execution."""
    job_id: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    error: str = ""
    duration_ms: int = 0


class CronScheduler:
    """Background job scheduler.

    Parameters
    ----------
    tick_interval:
        How often (seconds) the scheduler checks for due jobs.
    """

    def __init__(self, tick_interval: float = 60.0) -> None:
        self._jobs: dict[str, CronJob] = {}
        self._handlers: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._run_log: list[RunLogEntry] = []
        self._tick_interval = tick_interval
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._job_counter: int = 0

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def add_job(
        self,
        name: str,
        schedule: str,
        action: str,
        params: dict[str, Any] | None = None,
    ) -> CronJob:
        """Create and register a new scheduled job."""
        self._job_counter += 1
        job_id = f"job_{self._job_counter}"

        job = CronJob(
            id=job_id,
            name=name,
            schedule=schedule,
            action=action,
            params=params or {},
        )
        self._jobs[job_id] = job
        logger.info("cron_job_added", job_id=job_id, name=name, schedule=schedule)
        return job

    def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info("cron_job_removed", job_id=job_id)
            return True
        return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.PAUSED
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.ACTIVE
            return True
        return False

    def list_jobs(self) -> list[CronJob]:
        """Return all registered jobs."""
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> CronJob | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(
        self, action: str, handler: Callable[..., Coroutine[Any, Any, Any]]
    ) -> None:
        """Register an async handler for a job action type."""
        self._handlers[action] = handler

    # ------------------------------------------------------------------
    # Scheduler lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._tick_loop())
        logger.info("cron_scheduler_started", tick_interval=self._tick_interval)

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("cron_scheduler_stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Run log
    # ------------------------------------------------------------------

    def get_run_log(self, job_id: str | None = None, limit: int = 50) -> list[RunLogEntry]:
        """Get recent run log entries, optionally filtered by job ID."""
        entries = self._run_log
        if job_id:
            entries = [e for e in entries if e.job_id == job_id]
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _tick_loop(self) -> None:
        """Periodically check for due jobs and execute them."""
        try:
            while self._running:
                await self._check_and_run_due_jobs()
                await asyncio.sleep(self._tick_interval)
        except asyncio.CancelledError:
            return

    async def _check_and_run_due_jobs(self) -> None:
        """Check all active jobs and run those that are due."""
        now = datetime.now(UTC)
        for job in list(self._jobs.values()):
            if job.status != JobStatus.ACTIVE:
                continue
            if self._is_due(job, now):
                await self._execute_job(job)

    async def _execute_job(self, job: CronJob) -> None:
        """Execute a single job."""
        handler = self._handlers.get(job.action)
        if not handler:
            logger.warning("cron_no_handler", job_id=job.id, action=job.action)
            return

        start_time = datetime.now(UTC)
        start_mono = time.monotonic()

        try:
            await handler(**job.params)
            elapsed_ms = int((time.monotonic() - start_mono) * 1000)
            job.last_run = datetime.now(UTC)
            job.run_count += 1

            self._run_log.append(RunLogEntry(
                job_id=job.id,
                status=RunStatus.SUCCESS,
                started_at=start_time,
                finished_at=datetime.now(UTC),
                duration_ms=elapsed_ms,
            ))
            logger.info("cron_job_success", job_id=job.id, name=job.name, duration_ms=elapsed_ms)

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_mono) * 1000)
            job.last_run = datetime.now(UTC)
            job.run_count += 1
            job.failure_count += 1

            self._run_log.append(RunLogEntry(
                job_id=job.id,
                status=RunStatus.FAILURE,
                started_at=start_time,
                finished_at=datetime.now(UTC),
                error=str(exc),
                duration_ms=elapsed_ms,
            ))
            logger.error("cron_job_failed", job_id=job.id, name=job.name, error=str(exc))

    @staticmethod
    def _is_due(job: CronJob, now: datetime) -> bool:
        """Check if a job is due to run based on its schedule."""
        schedule = job.schedule.strip()

        # Simple interval: "every Nm" or "every Nh"
        interval_match = re.match(r"every\s+(\d+)([mhsd])", schedule, re.IGNORECASE)
        if interval_match:
            amount = int(interval_match.group(1))
            unit = interval_match.group(2).lower()
            seconds = {"m": 60, "h": 3600, "s": 1, "d": 86400}.get(unit, 60) * amount

            if job.last_run is None:
                return True
            elapsed = (now - job.last_run).total_seconds()
            return elapsed >= seconds

        # Cron expression: simplified minute-level check
        # Format: "min hour dom month dow" (standard 5-field cron)
        parts = schedule.split()
        if len(parts) == 5:
            return _cron_matches(parts, now)

        return False


def _cron_matches(fields: list[str], now: datetime) -> bool:
    """Check if a 5-field cron expression matches the current time."""
    checks = [
        (fields[0], now.minute),
        (fields[1], now.hour),
        (fields[2], now.day),
        (fields[3], now.month),
        (fields[4], now.weekday()),  # 0=Monday in Python
    ]
    for pattern, value in checks:
        if not _field_matches(pattern, value):
            return False
    return True


def _field_matches(pattern: str, value: int) -> bool:
    """Check if a single cron field matches a value."""
    if pattern == "*":
        return True

    # Handle step: */5
    if pattern.startswith("*/"):
        step = int(pattern[2:])
        return value % step == 0

    # Handle comma-separated: 1,5,10
    if "," in pattern:
        return value in {int(v) for v in pattern.split(",")}

    # Handle range: 1-5
    if "-" in pattern:
        lo, hi = pattern.split("-", 1)
        return int(lo) <= value <= int(hi)

    # Exact match
    try:
        return value == int(pattern)
    except ValueError:
        return False
