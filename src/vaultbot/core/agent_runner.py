"""Agent execution runner with fallback, memory dedup, and usage tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class RunState(str, Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    EXECUTING = "executing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass(slots=True)
class RunContext:
    run_id: str = ""
    session_id: str = ""
    agent_id: str = ""
    model: str = ""
    state: RunState = RunState.IDLE
    started_at: float = 0.0
    finished_at: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    fallback_attempts: int = 0
    memory_deduped: int = 0
    error: str = ""


@dataclass(frozen=True, slots=True)
class FallbackResult:
    model: str
    succeeded: bool
    error: str = ""
    attempt: int = 0


class AgentRunner:
    """Executes agent turns with fallback, memory management, and tracking."""

    def __init__(self) -> None:
        self._active_runs: dict[str, RunContext] = {}
        self._run_counter = 0
        self._total_runs = 0
        self._fallback_chain: list[str] = []

    def set_fallback_chain(self, models: list[str]) -> None:
        self._fallback_chain = models

    def start_run(self, session_id: str, agent_id: str = "", model: str = "") -> RunContext:
        self._run_counter += 1
        ctx = RunContext(
            run_id=f"run_{self._run_counter}",
            session_id=session_id,
            agent_id=agent_id,
            model=model or (self._fallback_chain[0] if self._fallback_chain else ""),
            state=RunState.PREPARING,
            started_at=time.time(),
        )
        self._active_runs[session_id] = ctx
        return ctx

    def execute(self, session_id: str) -> RunContext | None:
        ctx = self._active_runs.get(session_id)
        if not ctx:
            return None
        ctx.state = RunState.EXECUTING
        return ctx

    def complete_run(
        self, session_id: str, input_tokens: int = 0, output_tokens: int = 0
    ) -> RunContext | None:
        ctx = self._active_runs.pop(session_id, None)
        if not ctx:
            return None
        ctx.state = RunState.COMPLETED
        ctx.input_tokens = input_tokens
        ctx.output_tokens = output_tokens
        ctx.finished_at = time.time()
        self._total_runs += 1
        return ctx

    def fail_run(self, session_id: str, error: str = "") -> RunContext | None:
        ctx = self._active_runs.get(session_id)
        if not ctx:
            return None
        ctx.error = error
        # Try fallback
        fallback = self._try_fallback(ctx)
        if fallback and fallback.succeeded:
            ctx.model = fallback.model
            ctx.fallback_attempts += 1
            return ctx
        ctx.state = RunState.FAILED
        ctx.finished_at = time.time()
        self._active_runs.pop(session_id, None)
        return ctx

    def abort_run(self, session_id: str) -> bool:
        ctx = self._active_runs.pop(session_id, None)
        if not ctx:
            return False
        ctx.state = RunState.ABORTED
        ctx.finished_at = time.time()
        return True

    def get_active(self, session_id: str) -> RunContext | None:
        return self._active_runs.get(session_id)

    @property
    def active_count(self) -> int:
        return len(self._active_runs)

    @property
    def total_runs(self) -> int:
        return self._total_runs

    def _try_fallback(self, ctx: RunContext) -> FallbackResult | None:
        if not self._fallback_chain:
            return None
        try:
            idx = self._fallback_chain.index(ctx.model)
            if idx + 1 < len(self._fallback_chain):
                next_model = self._fallback_chain[idx + 1]
                return FallbackResult(
                    model=next_model, succeeded=True, attempt=ctx.fallback_attempts + 1
                )
        except ValueError:
            pass
        return None


def dedup_memory_entries(entries: list[dict[str, object]]) -> tuple[list[dict[str, object]], int]:
    """Deduplicate memory entries. Returns (deduped_list, removed_count)."""
    seen: set[str] = set()
    result: list[dict[str, object]] = []
    removed = 0
    for entry in entries:
        key = str(entry.get("content", ""))
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        result.append(entry)
    return result, removed
