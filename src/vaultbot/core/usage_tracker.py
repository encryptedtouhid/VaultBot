"""Token usage tracking and cost estimation."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Approximate costs per 1K tokens (USD)
_DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-20250514": (0.003, 0.015),
    "claude-opus-4-20250514": (0.015, 0.075),
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "deepseek-chat": (0.00014, 0.00028),
}


@dataclass(slots=True)
class UsageRecord:
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass(slots=True)
class SessionUsage:
    session_id: str = ""
    records: list[UsageRecord] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.estimated_cost_usd for r in self.records)

    @property
    def turn_count(self) -> int:
        return len(self.records)


class UsageTracker:
    """Track token usage and estimate costs across sessions."""

    def __init__(self, pricing: dict[str, tuple[float, float]] | None = None) -> None:
        self._pricing = pricing or dict(_DEFAULT_PRICING)
        self._sessions: dict[str, SessionUsage] = {}

    def record(
        self, session_id: str, model: str, input_tokens: int, output_tokens: int
    ) -> UsageRecord:
        input_cost, output_cost = self._pricing.get(model, (0.0, 0.0))
        cost = (input_tokens / 1000 * input_cost) + (output_tokens / 1000 * output_cost)
        record = UsageRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=round(cost, 6),
        )
        usage = self._sessions.setdefault(session_id, SessionUsage(session_id=session_id))
        usage.records.append(record)
        return record

    def get_session_usage(self, session_id: str) -> SessionUsage | None:
        return self._sessions.get(session_id)

    def get_total_cost(self) -> float:
        return sum(s.total_cost_usd for s in self._sessions.values())

    def format_usage(self, session_id: str) -> str:
        usage = self._sessions.get(session_id)
        if not usage:
            return "No usage data"
        return (
            f"Turns: {usage.turn_count} | "
            f"Tokens: {usage.total_input_tokens}↑ {usage.total_output_tokens}↓ | "
            f"Cost: ${usage.total_cost_usd:.4f}"
        )
