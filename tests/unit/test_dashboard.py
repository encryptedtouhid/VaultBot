"""Tests for the dashboard SSE broadcaster and events."""

import asyncio

from zenbot.dashboard.server import DashboardConfig, DashboardEvent, SSEBroadcaster


class TestDashboardEvent:
    def test_to_sse_format(self) -> None:
        event = DashboardEvent(event_type="message", data={"text": "hello"})
        sse = event.to_sse()
        assert "event: message\n" in sse
        assert "data: " in sse
        assert '"text": "hello"' in sse
        assert sse.endswith("\n\n")

    def test_event_type_in_payload(self) -> None:
        event = DashboardEvent(event_type="status", data={"ok": True})
        sse = event.to_sse()
        assert '"type": "status"' in sse


class TestSSEBroadcaster:
    def test_subscribe_creates_queue(self) -> None:
        broadcaster = SSEBroadcaster()
        queue = broadcaster.subscribe()
        assert broadcaster.client_count == 1
        assert isinstance(queue, asyncio.Queue)

    def test_unsubscribe_removes_queue(self) -> None:
        broadcaster = SSEBroadcaster()
        queue = broadcaster.subscribe()
        broadcaster.unsubscribe(queue)
        assert broadcaster.client_count == 0

    def test_multiple_subscribers(self) -> None:
        broadcaster = SSEBroadcaster()
        q1 = broadcaster.subscribe()
        broadcaster.subscribe()  # second subscriber
        assert broadcaster.client_count == 2
        broadcaster.unsubscribe(q1)
        assert broadcaster.client_count == 1


class TestDashboardConfig:
    def test_default_localhost(self) -> None:
        config = DashboardConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8082

    def test_auto_generated_token(self) -> None:
        config = DashboardConfig()
        assert len(config.api_token) > 20  # urlsafe token

    def test_unique_tokens(self) -> None:
        c1 = DashboardConfig()
        c2 = DashboardConfig()
        assert c1.api_token != c2.api_token


class TestMarketplaceEntry:
    def test_from_dict(self) -> None:
        from zenbot.plugins.marketplace import MarketplaceEntry, ReviewStatus

        entry = MarketplaceEntry.from_dict({
            "name": "weather",
            "version": "1.0",
            "description": "Weather plugin",
            "author": "dev",
            "review_status": "approved",
            "downloads": 100,
            "tags": ["weather", "api"],
        })
        assert entry.name == "weather"
        assert entry.review_status == ReviewStatus.APPROVED
        assert entry.downloads == 100
        assert "weather" in entry.tags
