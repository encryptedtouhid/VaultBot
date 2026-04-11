"""OpenTelemetry observability and metrics export.

Provides structured metrics, traces, and spans for monitoring
VaultBot in production environments.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Span:
    """A trace span representing a unit of work."""
    name: str
    trace_id: str
    span_id: str
    parent_span_id: str = ""
    start_time: float = field(default_factory=time.monotonic)
    end_time: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"

    @property
    def duration_ms(self) -> float:
        if self.end_time == 0:
            return (time.monotonic() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def end(self, status: str = "ok") -> None:
        self.end_time = time.monotonic()
        self.status = status


class MetricsExporter:
    """Collects and exports metrics in OpenTelemetry-compatible format."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._spans: list[Span] = []
        self._span_counter: int = 0

    def increment(self, name: str, value: int = 1, **labels: str) -> None:
        key = self._make_key(name, labels)
        self._counters[key] += value

    def gauge(self, name: str, value: float, **labels: str) -> None:
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def histogram(self, name: str, value: float, **labels: str) -> None:
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

    def start_span(self, name: str, trace_id: str = "", parent_span_id: str = "", **attrs: Any) -> Span:
        self._span_counter += 1
        span = Span(
            name=name,
            trace_id=trace_id or f"trace_{self._span_counter}",
            span_id=f"span_{self._span_counter}",
            parent_span_id=parent_span_id,
            attributes=attrs,
        )
        self._spans.append(span)
        return span

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_histogram_avg(self, name: str) -> float:
        values = self._histograms.get(name, [])
        return sum(values) / len(values) if values else 0.0

    def export_metrics(self) -> dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: {"count": len(v), "avg": sum(v) / len(v) if v else 0} for k, v in self._histograms.items()},
        }

    def export_spans(self, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {"name": s.name, "trace_id": s.trace_id, "span_id": s.span_id, "duration_ms": s.duration_ms, "status": s.status}
            for s in self._spans[-limit:]
        ]

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._spans.clear()

    @staticmethod
    def _make_key(name: str, labels: dict[str, str]) -> str:
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
