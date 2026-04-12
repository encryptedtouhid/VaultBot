"""Unit tests for block streaming."""

from __future__ import annotations

from vaultbot.core.block_streaming import (
    BackpressureConfig,
    BackpressureManager,
    BlockStreamingEngine,
    StreamingMode,
)


class TestBlockStreamingEngine:
    def test_token_mode(self) -> None:
        engine = BlockStreamingEngine(mode=StreamingMode.TOKEN)
        blocks = engine.add_token("hello")
        assert len(blocks) == 1
        assert blocks[0].content == "hello"

    def test_sentence_mode(self) -> None:
        engine = BlockStreamingEngine(mode=StreamingMode.SENTENCE)
        assert engine.add_token("Hello") == []
        assert engine.add_token(" world") == []
        blocks = engine.add_token(". Next")
        assert len(blocks) == 1
        assert "Hello world." in blocks[0].content

    def test_paragraph_mode(self) -> None:
        engine = BlockStreamingEngine(mode=StreamingMode.PARAGRAPH)
        assert engine.add_token("First paragraph.") == []
        blocks = engine.add_token("\n\nSecond")
        assert len(blocks) == 1

    def test_full_mode_buffers(self) -> None:
        engine = BlockStreamingEngine(mode=StreamingMode.FULL)
        assert engine.add_token("hello. ") == []
        assert engine.add_token("world. ") == []

    def test_flush(self) -> None:
        engine = BlockStreamingEngine(mode=StreamingMode.FULL)
        engine.add_token("buffered content")
        block = engine.flush()
        assert block is not None
        assert block.is_final is True
        assert block.content == "buffered content"

    def test_flush_empty(self) -> None:
        engine = BlockStreamingEngine()
        assert engine.flush() is None

    def test_blocks_emitted_count(self) -> None:
        engine = BlockStreamingEngine(mode=StreamingMode.TOKEN)
        engine.add_token("a")
        engine.add_token("b")
        assert engine.blocks_emitted == 2

    def test_code_block_no_split(self) -> None:
        engine = BlockStreamingEngine(mode=StreamingMode.SENTENCE)
        engine.add_token("```")
        blocks = engine.add_token("code. here. ")
        assert blocks == []  # Inside code block, no splitting

    def test_reset(self) -> None:
        engine = BlockStreamingEngine()
        engine.add_token("data")
        engine.reset()
        assert engine.flush() is None


class TestBackpressureManager:
    def test_enqueue_within_limit(self) -> None:
        mgr = BackpressureManager()
        assert mgr.enqueue() is True
        assert mgr.pending == 1

    def test_enqueue_exceeds_limit(self) -> None:
        config = BackpressureConfig(max_pending_blocks=2)
        mgr = BackpressureManager(config)
        mgr.enqueue()
        mgr.enqueue()
        assert mgr.enqueue() is False

    def test_acknowledge(self) -> None:
        mgr = BackpressureManager()
        mgr.enqueue()
        mgr.acknowledge()
        assert mgr.pending == 0
        assert mgr.delivered == 1

    def test_should_slow_down(self) -> None:
        config = BackpressureConfig(max_pending_blocks=4)
        mgr = BackpressureManager(config)
        mgr.enqueue()
        mgr.enqueue()
        assert mgr.should_slow_down() is False
        mgr.enqueue()
        assert mgr.should_slow_down() is True
