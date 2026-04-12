"""Workflow execution engine."""

from __future__ import annotations

import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from vaultbot.utils.logging import get_logger
from vaultbot.workflows.pipeline import Pipeline, PipelineStatus, PipelineStep

logger = get_logger(__name__)

StepHandler = Callable[[PipelineStep, dict[str, object]], Coroutine[Any, Any, dict[str, object]]]


@dataclass(frozen=True, slots=True)
class StepResult:
    step_id: str
    success: bool
    output: dict[str, object] = field(default_factory=dict)
    error: str = ""
    duration_ms: int = 0


@dataclass(frozen=True, slots=True)
class PipelineResult:
    pipeline_id: str
    status: PipelineStatus
    step_results: list[StepResult] = field(default_factory=list)
    total_duration_ms: int = 0


class WorkflowEngine:
    """Execute pipelines with step handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, StepHandler] = {}
        self._execution_count = 0

    def register_handler(self, step_type: str, handler: StepHandler) -> None:
        self._handlers[step_type] = handler

    @property
    def execution_count(self) -> int:
        return self._execution_count

    async def execute(self, pipeline: Pipeline) -> PipelineResult:
        """Execute a pipeline, running steps in order."""
        pipeline.status = PipelineStatus.RUNNING
        results: list[StepResult] = []
        context: dict[str, object] = dict(pipeline.variables)
        start = time.monotonic()

        for step in pipeline.steps:
            handler = self._handlers.get(step.step_type.value)
            if not handler:
                results.append(
                    StepResult(
                        step_id=step.step_id,
                        success=False,
                        error=f"No handler for {step.step_type.value}",
                    )
                )
                pipeline.status = PipelineStatus.FAILED
                break

            step_start = time.monotonic()
            try:
                output = await handler(step, context)
                context.update(output)
                results.append(
                    StepResult(
                        step_id=step.step_id,
                        success=True,
                        output=output,
                        duration_ms=int((time.monotonic() - step_start) * 1000),
                    )
                )
            except Exception as exc:
                results.append(
                    StepResult(
                        step_id=step.step_id,
                        success=False,
                        error=str(exc),
                        duration_ms=int((time.monotonic() - step_start) * 1000),
                    )
                )
                pipeline.status = PipelineStatus.FAILED
                break
        else:
            pipeline.status = PipelineStatus.COMPLETED

        self._execution_count += 1
        total_ms = int((time.monotonic() - start) * 1000)

        return PipelineResult(
            pipeline_id=pipeline.pipeline_id,
            status=pipeline.status,
            step_results=results,
            total_duration_ms=total_ms,
        )
