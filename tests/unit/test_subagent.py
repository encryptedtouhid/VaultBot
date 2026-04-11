"""Unit tests for sub-agent spawning and orchestration."""

from __future__ import annotations

import asyncio

import pytest

from vaultbot.agents.subagent import AgentStatus, SubAgent, SubAgentRegistry


# ---------------------------------------------------------------------------
# Spawn
# ---------------------------------------------------------------------------


class TestSubAgentSpawn:
    def test_spawn_basic(self) -> None:
        registry = SubAgentRegistry()
        agent = registry.spawn("research", "Find info about X")
        assert agent.id == "agent_1"
        assert agent.name == "research"
        assert agent.depth == 0
        assert agent.status == AgentStatus.PENDING

    def test_spawn_with_parent(self) -> None:
        registry = SubAgentRegistry()
        parent = registry.spawn("parent", "main task")
        child = registry.spawn("child", "subtask", parent_id=parent.id)
        assert child.depth == 1
        assert child.parent_id == parent.id

    def test_spawn_depth_limit(self) -> None:
        registry = SubAgentRegistry(max_depth=2)
        a1 = registry.spawn("a1", "task1")
        a2 = registry.spawn("a2", "task2", parent_id=a1.id)
        with pytest.raises(ValueError, match="Max agent depth"):
            registry.spawn("a3", "task3", parent_id=a2.id)

    def test_spawn_with_budget(self) -> None:
        registry = SubAgentRegistry()
        agent = registry.spawn("test", "task", token_budget=10000)
        assert agent.token_budget == 10000

    def test_spawn_with_timeout(self) -> None:
        registry = SubAgentRegistry()
        agent = registry.spawn("test", "task", timeout=60.0)
        assert agent.timeout == 60.0


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class TestSubAgentRun:
    @pytest.mark.asyncio
    async def test_run_success(self) -> None:
        registry = SubAgentRegistry()

        async def executor(task: str) -> str:
            return f"Done: {task}"

        registry.set_executor(executor)
        agent = registry.spawn("test", "analyze data")
        result = await registry.run(agent.id)

        assert result.status == AgentStatus.COMPLETED
        assert "Done: analyze data" in result.result
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_run_failure(self) -> None:
        registry = SubAgentRegistry()

        async def failing_executor(task: str) -> str:
            raise RuntimeError("agent crashed")

        registry.set_executor(failing_executor)
        agent = registry.spawn("test", "bad task")
        result = await registry.run(agent.id)

        assert result.status == AgentStatus.FAILED
        assert "agent crashed" in result.error

    @pytest.mark.asyncio
    async def test_run_timeout(self) -> None:
        registry = SubAgentRegistry()

        async def slow_executor(task: str) -> str:
            await asyncio.sleep(10)
            return "late"

        registry.set_executor(slow_executor)
        agent = registry.spawn("test", "slow task", timeout=0.05)
        result = await registry.run(agent.id)

        assert result.status == AgentStatus.TIMED_OUT

    @pytest.mark.asyncio
    async def test_run_unknown_agent(self) -> None:
        registry = SubAgentRegistry()
        registry.set_executor(lambda t: t)
        with pytest.raises(ValueError, match="Unknown agent"):
            await registry.run("nonexistent")

    @pytest.mark.asyncio
    async def test_run_no_executor(self) -> None:
        registry = SubAgentRegistry()
        agent = registry.spawn("test", "task")
        with pytest.raises(RuntimeError, match="No executor"):
            await registry.run(agent.id)


# ---------------------------------------------------------------------------
# Parallel execution
# ---------------------------------------------------------------------------


class TestSubAgentParallel:
    @pytest.mark.asyncio
    async def test_run_parallel(self) -> None:
        registry = SubAgentRegistry()
        results_order: list[str] = []

        async def executor(task: str) -> str:
            results_order.append(task)
            return f"Done: {task}"

        registry.set_executor(executor)
        a1 = registry.spawn("a1", "task1")
        a2 = registry.spawn("a2", "task2")
        a3 = registry.spawn("a3", "task3")

        results = await registry.run_parallel([a1.id, a2.id, a3.id])
        assert len(results) == 3
        assert all(r.status == AgentStatus.COMPLETED for r in results)


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


class TestSubAgentCancel:
    def test_cancel_pending(self) -> None:
        registry = SubAgentRegistry()
        agent = registry.spawn("test", "task")
        assert registry.cancel(agent.id) is True
        assert registry.get_agent(agent.id).status == AgentStatus.CANCELLED

    def test_cancel_completed_fails(self) -> None:
        registry = SubAgentRegistry()
        agent = registry.spawn("test", "task")
        agent.status = AgentStatus.COMPLETED
        assert registry.cancel(agent.id) is False

    def test_cancel_unknown(self) -> None:
        registry = SubAgentRegistry()
        assert registry.cancel("nonexistent") is False


# ---------------------------------------------------------------------------
# List and cleanup
# ---------------------------------------------------------------------------


class TestSubAgentManagement:
    def test_list_agents(self) -> None:
        registry = SubAgentRegistry()
        registry.spawn("a1", "t1")
        registry.spawn("a2", "t2")
        assert len(registry.list_agents()) == 2

    def test_list_by_parent(self) -> None:
        registry = SubAgentRegistry()
        parent = registry.spawn("parent", "main")
        registry.spawn("child1", "sub1", parent_id=parent.id)
        registry.spawn("child2", "sub2", parent_id=parent.id)
        registry.spawn("other", "other_task")

        children = registry.list_agents(parent_id=parent.id)
        assert len(children) == 2

    def test_cleanup_completed(self) -> None:
        registry = SubAgentRegistry()
        a1 = registry.spawn("a1", "t1")
        a2 = registry.spawn("a2", "t2")
        a1.status = AgentStatus.COMPLETED
        a2.status = AgentStatus.RUNNING

        removed = registry.cleanup_completed()
        assert removed == 1
        assert registry.total_count == 1

    def test_active_count(self) -> None:
        registry = SubAgentRegistry()
        a1 = registry.spawn("a1", "t1")
        a2 = registry.spawn("a2", "t2")
        a1.status = AgentStatus.RUNNING
        a2.status = AgentStatus.COMPLETED

        assert registry.active_count == 1

    def test_get_agent(self) -> None:
        registry = SubAgentRegistry()
        agent = registry.spawn("test", "task")
        assert registry.get_agent(agent.id) is agent
        assert registry.get_agent("nonexistent") is None
