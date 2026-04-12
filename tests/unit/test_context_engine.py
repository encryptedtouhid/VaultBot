"""Unit tests for context window manager."""

from __future__ import annotations

from vaultbot.core.window_manager import (
    ContextWindowManager,
    RetentionStrategy,
    WindowConfig,
)


class TestContextWindowManager:
    def test_add_entry(self) -> None:
        mgr = ContextWindowManager()
        mgr.add("hello world")
        assert mgr.entry_count == 1
        assert mgr.total_tokens > 0

    def test_get_window(self) -> None:
        mgr = ContextWindowManager()
        mgr.add("a")
        mgr.add("b")
        window = mgr.get_window()
        assert len(window) == 2

    def test_clear(self) -> None:
        mgr = ContextWindowManager()
        mgr.add("test")
        mgr.clear()
        assert mgr.entry_count == 0
        assert mgr.total_tokens == 0

    def test_fifo_trim(self) -> None:
        config = WindowConfig(max_tokens=10, reserve_tokens=0, strategy=RetentionStrategy.FIFO)
        mgr = ContextWindowManager(config)
        mgr.add("a" * 20)
        mgr.add("b" * 20)
        # Should have trimmed older entries
        assert mgr.total_tokens <= 10

    def test_priority_trim(self) -> None:
        config = WindowConfig(max_tokens=10, reserve_tokens=0, strategy=RetentionStrategy.PRIORITY)
        mgr = ContextWindowManager(config)
        mgr.add("low", priority=0)
        mgr.add("high", priority=10)
        mgr.add("overflow" * 5, priority=5)
        # Low priority should be trimmed first
        contents = [e.content for e in mgr.get_window()]
        assert "low" not in contents or mgr.total_tokens <= 10

    def test_relevance_trim(self) -> None:
        config = WindowConfig(max_tokens=10, reserve_tokens=0, strategy=RetentionStrategy.RELEVANCE)
        mgr = ContextWindowManager(config)
        mgr.add("irrelevant", relevance=0.1)
        mgr.add("relevant", relevance=0.9)
        mgr.add("overflow" * 5, relevance=0.5)
        assert mgr.total_tokens <= 10

    def test_estimate_tokens(self) -> None:
        tokens = ContextWindowManager._estimate_tokens("hello world")
        assert tokens >= 1
