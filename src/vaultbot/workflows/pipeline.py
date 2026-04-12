"""Pipeline definition types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StepType(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    CONDITION = "condition"
    TRANSFORM = "transform"
    PARALLEL = "parallel"
    LOOP = "loop"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class PipelineStep:
    step_id: str = ""
    name: str = ""
    step_type: StepType = StepType.TOOL_CALL
    config: dict[str, object] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Pipeline:
    pipeline_id: str = ""
    name: str = ""
    description: str = ""
    steps: list[PipelineStep] = field(default_factory=list)
    status: PipelineStatus = PipelineStatus.PENDING
    variables: dict[str, object] = field(default_factory=dict)
