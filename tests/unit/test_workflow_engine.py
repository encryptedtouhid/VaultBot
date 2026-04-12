"""Unit tests for workflow engine."""

from __future__ import annotations

import pytest

from vaultbot.workflows.engine import WorkflowEngine
from vaultbot.workflows.pipeline import (
    Pipeline,
    PipelineStatus,
    PipelineStep,
    StepType,
)


class TestPipeline:
    def test_defaults(self) -> None:
        p = Pipeline(pipeline_id="p1", name="test")
        assert p.status == PipelineStatus.PENDING
        assert p.steps == []

    def test_step_defaults(self) -> None:
        s = PipelineStep(step_id="s1", name="step1")
        assert s.step_type == StepType.TOOL_CALL


class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_execute_empty_pipeline(self) -> None:
        engine = WorkflowEngine()
        pipeline = Pipeline(pipeline_id="p1", name="empty")
        result = await engine.execute(pipeline)
        assert result.status == PipelineStatus.COMPLETED
        assert result.step_results == []
        assert engine.execution_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_handler(self) -> None:
        engine = WorkflowEngine()

        async def tool_handler(step, ctx):
            return {"result": "done"}

        engine.register_handler("tool_call", tool_handler)

        pipeline = Pipeline(
            pipeline_id="p1",
            name="test",
            steps=[PipelineStep(step_id="s1", name="step1", step_type=StepType.TOOL_CALL)],
        )
        result = await engine.execute(pipeline)
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.step_results) == 1
        assert result.step_results[0].success is True

    @pytest.mark.asyncio
    async def test_execute_no_handler_fails(self) -> None:
        engine = WorkflowEngine()
        pipeline = Pipeline(
            pipeline_id="p1",
            name="test",
            steps=[PipelineStep(step_id="s1", name="step1", step_type=StepType.LLM_CALL)],
        )
        result = await engine.execute(pipeline)
        assert result.status == PipelineStatus.FAILED
        assert result.step_results[0].success is False

    @pytest.mark.asyncio
    async def test_execute_handler_exception(self) -> None:
        engine = WorkflowEngine()

        async def bad_handler(step, ctx):
            raise RuntimeError("boom")

        engine.register_handler("tool_call", bad_handler)

        pipeline = Pipeline(
            pipeline_id="p1",
            name="test",
            steps=[PipelineStep(step_id="s1", step_type=StepType.TOOL_CALL)],
        )
        result = await engine.execute(pipeline)
        assert result.status == PipelineStatus.FAILED
        assert "boom" in result.step_results[0].error

    @pytest.mark.asyncio
    async def test_multi_step_pipeline(self) -> None:
        engine = WorkflowEngine()

        async def handler(step, ctx):
            return {"x": ctx.get("x", 0) + 1}  # type: ignore[operator]

        engine.register_handler("tool_call", handler)

        pipeline = Pipeline(
            pipeline_id="p1",
            name="multi",
            steps=[
                PipelineStep(step_id="s1", step_type=StepType.TOOL_CALL),
                PipelineStep(step_id="s2", step_type=StepType.TOOL_CALL),
            ],
            variables={"x": 0},
        )
        result = await engine.execute(pipeline)
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.step_results) == 2
