"""Unit tests for agent runner."""

from __future__ import annotations

from vaultbot.core.agent_runner import AgentRunner, RunState, dedup_memory_entries


class TestAgentRunner:
    def test_start_run(self) -> None:
        runner = AgentRunner()
        runner.set_fallback_chain(["gpt-4o", "gpt-4o-mini"])
        ctx = runner.start_run("s1", agent_id="a1")
        assert ctx.state == RunState.PREPARING
        assert ctx.model == "gpt-4o"
        assert runner.active_count == 1

    def test_execute(self) -> None:
        runner = AgentRunner()
        runner.start_run("s1")
        ctx = runner.execute("s1")
        assert ctx is not None
        assert ctx.state == RunState.EXECUTING

    def test_complete_run(self) -> None:
        runner = AgentRunner()
        runner.start_run("s1")
        ctx = runner.complete_run("s1", input_tokens=100, output_tokens=50)
        assert ctx is not None
        assert ctx.state == RunState.COMPLETED
        assert runner.total_runs == 1
        assert runner.active_count == 0

    def test_fail_with_fallback(self) -> None:
        runner = AgentRunner()
        runner.set_fallback_chain(["gpt-4o", "gpt-4o-mini", "gpt-3.5"])
        runner.start_run("s1", model="gpt-4o")
        ctx = runner.fail_run("s1", error="rate limited")
        assert ctx is not None
        assert ctx.model == "gpt-4o-mini"
        assert ctx.fallback_attempts == 1

    def test_fail_no_fallback(self) -> None:
        runner = AgentRunner()
        runner.start_run("s1", model="only-model")
        ctx = runner.fail_run("s1", error="error")
        assert ctx is not None
        assert ctx.state == RunState.FAILED

    def test_abort(self) -> None:
        runner = AgentRunner()
        runner.start_run("s1")
        assert runner.abort_run("s1") is True
        assert runner.active_count == 0


class TestDedupMemory:
    def test_dedup(self) -> None:
        entries = [
            {"content": "hello"},
            {"content": "world"},
            {"content": "hello"},
        ]
        result, removed = dedup_memory_entries(entries)
        assert len(result) == 2
        assert removed == 1

    def test_no_dupes(self) -> None:
        entries = [{"content": "a"}, {"content": "b"}]
        result, removed = dedup_memory_entries(entries)
        assert removed == 0
