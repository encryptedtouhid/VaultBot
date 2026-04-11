"""Unit tests for cron scheduler."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from vaultbot.cron.scheduler import (
    CronJob,
    CronScheduler,
    JobStatus,
    RunStatus,
    _cron_matches,
    _field_matches,
)

# ---------------------------------------------------------------------------
# Cron expression parsing
# ---------------------------------------------------------------------------


class TestFieldMatches:
    def test_wildcard(self) -> None:
        assert _field_matches("*", 0) is True
        assert _field_matches("*", 59) is True

    def test_exact(self) -> None:
        assert _field_matches("5", 5) is True
        assert _field_matches("5", 6) is False

    def test_step(self) -> None:
        assert _field_matches("*/5", 0) is True
        assert _field_matches("*/5", 5) is True
        assert _field_matches("*/5", 3) is False

    def test_range(self) -> None:
        assert _field_matches("1-5", 3) is True
        assert _field_matches("1-5", 6) is False

    def test_comma_list(self) -> None:
        assert _field_matches("1,5,10", 5) is True
        assert _field_matches("1,5,10", 3) is False

    def test_invalid(self) -> None:
        assert _field_matches("abc", 0) is False


class TestCronMatches:
    def test_every_minute(self) -> None:
        now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        assert _cron_matches(["*", "*", "*", "*", "*"], now) is True

    def test_specific_minute(self) -> None:
        now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        assert _cron_matches(["30", "*", "*", "*", "*"], now) is True
        assert _cron_matches(["15", "*", "*", "*", "*"], now) is False

    def test_every_5_minutes(self) -> None:
        now = datetime(2024, 1, 15, 10, 15, tzinfo=UTC)
        assert _cron_matches(["*/5", "*", "*", "*", "*"], now) is True


# ---------------------------------------------------------------------------
# Scheduler job management
# ---------------------------------------------------------------------------


class TestCronSchedulerJobs:
    def test_add_job(self) -> None:
        scheduler = CronScheduler()
        job = scheduler.add_job("test", "every 5m", "send_message")
        assert job.id == "job_1"
        assert job.name == "test"
        assert job.status == JobStatus.ACTIVE

    def test_add_multiple_jobs(self) -> None:
        scheduler = CronScheduler()
        scheduler.add_job("j1", "every 1m", "action1")
        scheduler.add_job("j2", "every 2m", "action2")
        assert len(scheduler.list_jobs()) == 2

    def test_remove_job(self) -> None:
        scheduler = CronScheduler()
        job = scheduler.add_job("test", "every 5m", "action")
        assert scheduler.remove_job(job.id) is True
        assert len(scheduler.list_jobs()) == 0

    def test_remove_nonexistent(self) -> None:
        scheduler = CronScheduler()
        assert scheduler.remove_job("nonexistent") is False

    def test_pause_job(self) -> None:
        scheduler = CronScheduler()
        job = scheduler.add_job("test", "every 5m", "action")
        scheduler.pause_job(job.id)
        assert scheduler.get_job(job.id).status == JobStatus.PAUSED

    def test_resume_job(self) -> None:
        scheduler = CronScheduler()
        job = scheduler.add_job("test", "every 5m", "action")
        scheduler.pause_job(job.id)
        scheduler.resume_job(job.id)
        assert scheduler.get_job(job.id).status == JobStatus.ACTIVE

    def test_get_job(self) -> None:
        scheduler = CronScheduler()
        job = scheduler.add_job("test", "every 5m", "action")
        found = scheduler.get_job(job.id)
        assert found is not None
        assert found.name == "test"

    def test_get_nonexistent_job(self) -> None:
        scheduler = CronScheduler()
        assert scheduler.get_job("nonexistent") is None


# ---------------------------------------------------------------------------
# Is due logic
# ---------------------------------------------------------------------------


class TestIsDue:
    def test_interval_first_run(self) -> None:
        job = CronJob(id="j1", name="test", schedule="every 5m", action="act")
        now = datetime.now(UTC)
        assert CronScheduler._is_due(job, now) is True

    def test_interval_not_elapsed(self) -> None:
        job = CronJob(id="j1", name="test", schedule="every 5m", action="act")
        job.last_run = datetime.now(UTC)
        now = datetime.now(UTC)
        assert CronScheduler._is_due(job, now) is False

    def test_interval_hours(self) -> None:
        job = CronJob(id="j1", name="test", schedule="every 1h", action="act")
        assert CronScheduler._is_due(job, datetime.now(UTC)) is True

    def test_interval_days(self) -> None:
        job = CronJob(id="j1", name="test", schedule="every 1d", action="act")
        assert CronScheduler._is_due(job, datetime.now(UTC)) is True

    def test_cron_expression(self) -> None:
        job = CronJob(id="j1", name="test", schedule="* * * * *", action="act")
        assert CronScheduler._is_due(job, datetime.now(UTC)) is True


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class TestCronExecution:
    @pytest.mark.asyncio
    async def test_execute_job_success(self) -> None:
        scheduler = CronScheduler()
        executed = []

        async def handler(**kwargs: object) -> None:
            executed.append(kwargs)

        scheduler.register_handler("test_action", handler)
        job = scheduler.add_job("test", "every 1s", "test_action", {"key": "value"})

        await scheduler._execute_job(job)

        assert len(executed) == 1
        assert executed[0]["key"] == "value"
        assert job.run_count == 1
        assert job.failure_count == 0

        log = scheduler.get_run_log(job.id)
        assert len(log) == 1
        assert log[0].status == RunStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_job_failure(self) -> None:
        scheduler = CronScheduler()

        async def failing_handler(**kwargs: object) -> None:
            raise RuntimeError("job failed")

        scheduler.register_handler("fail_action", failing_handler)
        job = scheduler.add_job("test", "every 1s", "fail_action")

        await scheduler._execute_job(job)

        assert job.run_count == 1
        assert job.failure_count == 1

        log = scheduler.get_run_log(job.id)
        assert log[0].status == RunStatus.FAILURE
        assert "job failed" in log[0].error

    @pytest.mark.asyncio
    async def test_execute_no_handler(self) -> None:
        scheduler = CronScheduler()
        job = scheduler.add_job("test", "every 1s", "no_handler")
        await scheduler._execute_job(job)
        assert job.run_count == 0  # Not executed


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


class TestCronLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        scheduler = CronScheduler(tick_interval=0.01)
        await scheduler.start()
        assert scheduler.is_running is True
        await scheduler.stop()
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_stop_idempotent(self) -> None:
        scheduler = CronScheduler()
        await scheduler.stop()
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_run_log_filtered_by_job(self) -> None:
        scheduler = CronScheduler()
        scheduler._run_log.append(
            __import__("vaultbot.cron.scheduler", fromlist=["RunLogEntry"]).RunLogEntry(
                job_id="j1", status=RunStatus.SUCCESS, started_at=datetime.now(UTC)
            )
        )
        scheduler._run_log.append(
            __import__("vaultbot.cron.scheduler", fromlist=["RunLogEntry"]).RunLogEntry(
                job_id="j2", status=RunStatus.SUCCESS, started_at=datetime.now(UTC)
            )
        )
        assert len(scheduler.get_run_log("j1")) == 1
        assert len(scheduler.get_run_log()) == 2
