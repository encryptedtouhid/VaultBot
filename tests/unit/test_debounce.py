"""Unit tests for message debounce."""

from __future__ import annotations

from vaultbot.core.debounce import (
    DebounceConfig,
    DebounceEngine,
    coalesce_messages,
    looks_incomplete,
)


class TestHelpers:
    def test_looks_incomplete(self) -> None:
        assert looks_incomplete("hello...") is True
        assert looks_incomplete("I want to and") is True
        assert looks_incomplete("Hello world") is False
        assert looks_incomplete("") is False

    def test_coalesce_messages(self) -> None:
        assert coalesce_messages(["a", "b"]) == "a\nb"

    def test_coalesce_deduplicates(self) -> None:
        assert coalesce_messages(["hi", "hi", "there"]) == "hi\nthere"


class TestDebounceEngine:
    def test_disabled_returns_true(self) -> None:
        engine = DebounceEngine(DebounceConfig(enabled=False))
        assert engine.add_message("k", "hi") is True

    def test_first_message_buffered(self) -> None:
        engine = DebounceEngine()
        assert engine.add_message("k", "hi") is False
        assert engine.pending_count == 1

    def test_flush(self) -> None:
        engine = DebounceEngine()
        engine.add_message("k", "hello")
        engine.add_message("k", "world")
        result = engine.flush("k")
        assert result == "hello\nworld"
        assert engine.pending_count == 0

    def test_flush_empty(self) -> None:
        engine = DebounceEngine()
        assert engine.flush("nope") is None

    def test_flush_all(self) -> None:
        engine = DebounceEngine()
        engine.add_message("a", "msg1")
        engine.add_message("b", "msg2")
        results = engine.flush_all()
        assert len(results) == 2
        assert engine.pending_count == 0

    def test_max_wait_triggers_flush(self) -> None:
        engine = DebounceEngine(DebounceConfig(max_wait_ms=0))
        engine.add_message("k", "first")
        assert engine.add_message("k", "second") is True
