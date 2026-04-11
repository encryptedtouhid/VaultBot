"""Real-time metrics collection for the dashboard.

Tracks messages, LLM usage, active sessions, error rates, and costs
for display in the web dashboard.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class MetricSnapshot:
    """Point-in-time metric reading."""
    timestamp: datetime
    value: float
    label: str = ""


@dataclass
class DashboardMetrics:
    """Aggregated metrics for the dashboard."""
    messages_total: int = 0
    messages_per_minute: float = 0.0
    active_sessions: int = 0
    llm_requests_total: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_avg_latency_ms: float = 0.0
    errors_total: int = 0
    error_rate_per_minute: float = 0.0
    platforms_connected: int = 0
    platforms_total: int = 0
    uptime_seconds: float = 0.0


class MetricsCollector:
    """Collects and aggregates real-time metrics.

    Uses sliding windows for rate calculations.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._start_time = time.monotonic()

        # Counters
        self._messages_total: int = 0
        self._llm_requests_total: int = 0
        self._llm_input_tokens: int = 0
        self._llm_output_tokens: int = 0
        self._errors_total: int = 0

        # Sliding windows for rate calculation
        self._message_times: deque[float] = deque()
        self._error_times: deque[float] = deque()
        self._llm_latencies: deque[float] = deque(maxlen=100)

        # Platform tracking
        self._platforms_connected: int = 0
        self._platforms_total: int = 0
        self._active_sessions: int = 0

    def record_message(self) -> None:
        """Record an incoming message."""
        self._messages_total += 1
        self._message_times.append(time.monotonic())

    def record_llm_request(
        self, input_tokens: int, output_tokens: int, latency_ms: float
    ) -> None:
        """Record an LLM API request."""
        self._llm_requests_total += 1
        self._llm_input_tokens += input_tokens
        self._llm_output_tokens += output_tokens
        self._llm_latencies.append(latency_ms)

    def record_error(self) -> None:
        """Record an error."""
        self._errors_total += 1
        self._error_times.append(time.monotonic())

    def set_platform_status(self, connected: int, total: int) -> None:
        """Update platform connection counts."""
        self._platforms_connected = connected
        self._platforms_total = total

    def set_active_sessions(self, count: int) -> None:
        """Update active session count."""
        self._active_sessions = count

    def get_metrics(self) -> DashboardMetrics:
        """Get current aggregated metrics."""
        now = time.monotonic()

        # Clean old entries from sliding windows
        cutoff = now - self._window
        while self._message_times and self._message_times[0] < cutoff:
            self._message_times.popleft()
        while self._error_times and self._error_times[0] < cutoff:
            self._error_times.popleft()

        # Calculate rates
        msg_rate = len(self._message_times) / (self._window / 60.0) if self._window else 0
        err_rate = len(self._error_times) / (self._window / 60.0) if self._window else 0

        # Average LLM latency
        avg_latency = (
            sum(self._llm_latencies) / len(self._llm_latencies)
            if self._llm_latencies else 0.0
        )

        return DashboardMetrics(
            messages_total=self._messages_total,
            messages_per_minute=round(msg_rate, 1),
            active_sessions=self._active_sessions,
            llm_requests_total=self._llm_requests_total,
            llm_input_tokens=self._llm_input_tokens,
            llm_output_tokens=self._llm_output_tokens,
            llm_avg_latency_ms=round(avg_latency, 1),
            errors_total=self._errors_total,
            error_rate_per_minute=round(err_rate, 1),
            platforms_connected=self._platforms_connected,
            platforms_total=self._platforms_total,
            uptime_seconds=round(now - self._start_time, 1),
        )

    def reset(self) -> None:
        """Reset all metrics."""
        self._messages_total = 0
        self._llm_requests_total = 0
        self._llm_input_tokens = 0
        self._llm_output_tokens = 0
        self._errors_total = 0
        self._message_times.clear()
        self._error_times.clear()
        self._llm_latencies.clear()
        self._start_time = time.monotonic()
