"""Unit tests for dashboard metrics."""

from __future__ import annotations

from vaultbot.dashboard.metrics import DashboardMetrics, MetricsCollector


class TestDashboardMetrics:
    def test_defaults(self) -> None:
        m = DashboardMetrics()
        assert m.messages_total == 0
        assert m.active_sessions == 0
        assert m.uptime_seconds == 0.0


class TestMetricsCollector:
    def test_initial_metrics(self) -> None:
        collector = MetricsCollector()
        m = collector.get_metrics()
        assert m.messages_total == 0
        assert m.uptime_seconds >= 0

    def test_record_message(self) -> None:
        collector = MetricsCollector()
        collector.record_message()
        collector.record_message()
        m = collector.get_metrics()
        assert m.messages_total == 2

    def test_record_llm_request(self) -> None:
        collector = MetricsCollector()
        collector.record_llm_request(100, 50, 250.0)
        m = collector.get_metrics()
        assert m.llm_requests_total == 1
        assert m.llm_input_tokens == 100
        assert m.llm_output_tokens == 50
        assert m.llm_avg_latency_ms == 250.0

    def test_multiple_llm_requests_avg_latency(self) -> None:
        collector = MetricsCollector()
        collector.record_llm_request(10, 5, 100.0)
        collector.record_llm_request(10, 5, 300.0)
        m = collector.get_metrics()
        assert m.llm_avg_latency_ms == 200.0

    def test_record_error(self) -> None:
        collector = MetricsCollector()
        collector.record_error()
        m = collector.get_metrics()
        assert m.errors_total == 1

    def test_platform_status(self) -> None:
        collector = MetricsCollector()
        collector.set_platform_status(connected=5, total=7)
        m = collector.get_metrics()
        assert m.platforms_connected == 5
        assert m.platforms_total == 7

    def test_active_sessions(self) -> None:
        collector = MetricsCollector()
        collector.set_active_sessions(10)
        m = collector.get_metrics()
        assert m.active_sessions == 10

    def test_messages_per_minute(self) -> None:
        collector = MetricsCollector(window_seconds=60.0)
        for _ in range(5):
            collector.record_message()
        m = collector.get_metrics()
        assert m.messages_per_minute == 5.0

    def test_uptime(self) -> None:
        collector = MetricsCollector()
        m = collector.get_metrics()
        assert m.uptime_seconds >= 0

    def test_reset(self) -> None:
        collector = MetricsCollector()
        collector.record_message()
        collector.record_error()
        collector.record_llm_request(10, 5, 100)
        collector.reset()
        m = collector.get_metrics()
        assert m.messages_total == 0
        assert m.errors_total == 0
        assert m.llm_requests_total == 0

    def test_token_accumulation(self) -> None:
        collector = MetricsCollector()
        collector.record_llm_request(100, 50, 100)
        collector.record_llm_request(200, 100, 200)
        m = collector.get_metrics()
        assert m.llm_input_tokens == 300
        assert m.llm_output_tokens == 150
