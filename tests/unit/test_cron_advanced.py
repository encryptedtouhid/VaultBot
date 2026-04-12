"""Unit tests for advanced cron."""

from __future__ import annotations

from vaultbot.cron.isolated_runner import IsolatedRunner, RunnerState


class TestIsolatedRunner:
    def test_create_run(self) -> None:
        runner = IsolatedRunner()
        run = runner.create_run("job1", agent_id="a1", model="gpt-4o")
        assert run.state == RunnerState.IDLE
        assert runner.run_count == 1

    def test_start_run(self) -> None:
        runner = IsolatedRunner()
        run = runner.create_run("job1")
        assert runner.start_run(run.run_id) is True
        assert run.state == RunnerState.RUNNING

    def test_complete_run(self) -> None:
        runner = IsolatedRunner()
        run = runner.create_run("job1")
        runner.start_run(run.run_id)
        assert runner.complete_run(run.run_id, "done") is True
        assert run.state == RunnerState.COMPLETED

    def test_fail_run(self) -> None:
        runner = IsolatedRunner()
        run = runner.create_run("job1")
        runner.start_run(run.run_id)
        assert runner.fail_run(run.run_id, "error") is True
        assert run.state == RunnerState.FAILED

    def test_list_by_job(self) -> None:
        runner = IsolatedRunner()
        runner.create_run("job1")
        runner.create_run("job1")
        runner.create_run("job2")
        assert len(runner.list_by_job("job1")) == 2
