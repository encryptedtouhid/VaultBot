"""Unit tests for broadcast system."""

from __future__ import annotations

import pytest

from vaultbot.core.broadcast import BroadcastManager, BroadcastState, BroadcastTarget


class TestBroadcastManager:
    def test_create(self) -> None:
        mgr = BroadcastManager()
        targets = [BroadcastTarget(platform="tg", channel_id="c1")]
        b = mgr.create("News", "Hello!", targets)
        assert b.state == BroadcastState.DRAFT
        assert mgr.broadcast_count == 1

    def test_get(self) -> None:
        mgr = BroadcastManager()
        b = mgr.create("Test", "msg", [])
        assert mgr.get(b.broadcast_id) is not None
        assert mgr.get("nope") is None

    @pytest.mark.asyncio
    async def test_send(self) -> None:
        mgr = BroadcastManager()
        targets = [
            BroadcastTarget(platform="tg", channel_id="c1"),
            BroadcastTarget(platform="discord", channel_id="c2"),
        ]
        b = mgr.create("News", "Hello!", targets)
        result = await mgr.send(b.broadcast_id)
        assert result is not None
        assert result.state == BroadcastState.COMPLETED
        assert all(t.sent for t in result.targets)

    @pytest.mark.asyncio
    async def test_send_unknown(self) -> None:
        mgr = BroadcastManager()
        assert await mgr.send("nope") is None

    def test_stats(self) -> None:
        mgr = BroadcastManager()
        targets = [
            BroadcastTarget(platform="tg", channel_id="c1", sent=True),
            BroadcastTarget(platform="discord", channel_id="c2"),
        ]
        b = mgr.create("Test", "msg", targets)
        stats = mgr.get_stats(b.broadcast_id)
        assert stats["total"] == 2
        assert stats["sent"] == 1
