"""Cron job management CLI commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CronJobInfo:
    job_id: str
    name: str
    schedule: str
    action: str
    enabled: bool = True
    last_run: str = ""
    next_run: str = ""


class CronCommands:
    """CLI commands for cron job management."""

    def __init__(self) -> None:
        self._jobs: dict[str, CronJobInfo] = {}

    def create(self, name: str, schedule: str, action: str) -> CronJobInfo:
        job_id = f"cron_{len(self._jobs) + 1}"
        job = CronJobInfo(job_id=job_id, name=name, schedule=schedule, action=action)
        self._jobs[job_id] = job
        return job

    def delete(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    def list_jobs(self) -> list[CronJobInfo]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> CronJobInfo | None:
        return self._jobs.get(job_id)
