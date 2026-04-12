"""Unit tests for advanced auto-reply system."""

from __future__ import annotations

import pytest

from vaultbot.core.command_registry import (
    CommandDefinition,
    CommandRegistry,
)
from vaultbot.core.directives import extract_directives
from vaultbot.core.reply_pipeline import ReplyPipeline, ReplyState
from vaultbot.core.usage_tracker import UsageTracker

# ---------------------------------------------------------------------------
# Command Registry
# ---------------------------------------------------------------------------


class TestCommandRegistry:
    def test_register_and_resolve(self) -> None:
        reg = CommandRegistry()

        async def handler() -> str:
            return "ok"

        reg.register(CommandDefinition(name="help", description="Show help"), handler)
        assert reg.resolve("help") is not None

    def test_resolve_alias(self) -> None:
        reg = CommandRegistry()

        async def handler() -> str:
            return "ok"

        reg.register(
            CommandDefinition(name="help", aliases=["h", "?"]),
            handler,
        )
        assert reg.resolve("h") is not None
        assert reg.resolve("?") is not None

    def test_resolve_unknown(self) -> None:
        reg = CommandRegistry()
        assert reg.resolve("nope") is None

    def test_parse_command(self) -> None:
        reg = CommandRegistry()
        result = reg.parse_command("/help topic")
        assert result == ("help", ["topic"])

    def test_parse_no_args(self) -> None:
        reg = CommandRegistry()
        result = reg.parse_command("/status")
        assert result == ("status", [])

    def test_parse_not_command(self) -> None:
        reg = CommandRegistry()
        assert reg.parse_command("hello world") is None

    @pytest.mark.asyncio
    async def test_execute_command(self) -> None:
        reg = CommandRegistry()

        async def greet(name: str = "world") -> str:
            return f"Hello {name}"

        reg.register(CommandDefinition(name="greet"), greet)
        result = await reg.execute("/greet Alice")
        assert result == "Hello Alice"

    @pytest.mark.asyncio
    async def test_execute_not_command(self) -> None:
        reg = CommandRegistry()
        assert await reg.execute("just text") is None

    def test_autocomplete(self) -> None:
        reg = CommandRegistry()

        async def handler() -> str:
            return ""

        reg.register(CommandDefinition(name="help"), handler)
        reg.register(CommandDefinition(name="history"), handler)
        reg.register(CommandDefinition(name="status"), handler)
        matches = reg.autocomplete("h")
        assert "/help" in matches
        assert "/history" in matches
        assert "/status" not in matches

    def test_list_commands(self) -> None:
        reg = CommandRegistry()

        async def handler() -> str:
            return ""

        reg.register(CommandDefinition(name="a"), handler)
        reg.register(CommandDefinition(name="b"), handler)
        assert len(reg.list_commands()) == 2


# ---------------------------------------------------------------------------
# Directives
# ---------------------------------------------------------------------------


class TestDirectives:
    def test_extract_model(self) -> None:
        d = extract_directives("/model gpt-4o\nhello")
        assert d.model == "gpt-4o"
        assert "hello" in d.clean_text

    def test_extract_thinking(self) -> None:
        d = extract_directives("thinking: on\nWhat is 2+2?")
        assert d.thinking is True

    def test_extract_verbose(self) -> None:
        d = extract_directives("verbose: yes explain this")
        assert d.verbose is True

    def test_extract_abort(self) -> None:
        d = extract_directives("/abort")
        assert d.abort is True

    def test_extract_queue(self) -> None:
        d = extract_directives("/queue")
        assert d.queue is True

    def test_no_directives(self) -> None:
        d = extract_directives("just a normal message")
        assert d.model == ""
        assert d.thinking is False
        assert d.clean_text == "just a normal message"

    def test_clean_text_strips_directives(self) -> None:
        d = extract_directives("/model gpt-4o\nHello world")
        assert "/model" not in d.clean_text


# ---------------------------------------------------------------------------
# Reply Pipeline
# ---------------------------------------------------------------------------


class TestReplyPipeline:
    def test_start_reply(self) -> None:
        pipe = ReplyPipeline()
        ctx = pipe.start_reply("s1", "hello", model="gpt-4o")
        assert ctx.state == ReplyState.PROCESSING
        assert pipe.active_count == 1

    def test_stream_chunk(self) -> None:
        pipe = ReplyPipeline()
        pipe.start_reply("s1", "hello")
        assert pipe.stream_chunk("s1", "Hi") is True
        assert pipe.stream_chunk("s1", " there") is True
        ctx = pipe.get_active("s1")
        assert ctx is not None
        assert ctx.output_text == "Hi there"

    def test_complete_reply(self) -> None:
        pipe = ReplyPipeline()
        pipe.start_reply("s1", "hello")
        pipe.stream_chunk("s1", "response")
        ctx = pipe.complete_reply("s1")
        assert ctx is not None
        assert ctx.state == ReplyState.COMPLETED
        assert pipe.active_count == 0

    def test_abort_reply(self) -> None:
        pipe = ReplyPipeline()
        pipe.start_reply("s1", "hello")
        assert pipe.abort_reply("s1") is True
        assert pipe.active_count == 0

    def test_stream_after_abort(self) -> None:
        pipe = ReplyPipeline()
        pipe.start_reply("s1", "hello")
        pipe.abort_reply("s1")
        assert pipe.stream_chunk("s1", "data") is False

    def test_fail_reply(self) -> None:
        pipe = ReplyPipeline()
        pipe.start_reply("s1", "hello")
        assert pipe.fail_reply("s1", "error") is True


# ---------------------------------------------------------------------------
# Usage Tracker
# ---------------------------------------------------------------------------


class TestUsageTracker:
    def test_record_usage(self) -> None:
        tracker = UsageTracker()
        record = tracker.record("s1", "gpt-4o", 100, 50)
        assert record.input_tokens == 100
        assert record.estimated_cost_usd > 0

    def test_session_totals(self) -> None:
        tracker = UsageTracker()
        tracker.record("s1", "gpt-4o", 100, 50)
        tracker.record("s1", "gpt-4o", 200, 100)
        usage = tracker.get_session_usage("s1")
        assert usage is not None
        assert usage.total_input_tokens == 300
        assert usage.turn_count == 2

    def test_unknown_model_zero_cost(self) -> None:
        tracker = UsageTracker()
        record = tracker.record("s1", "unknown-model", 100, 50)
        assert record.estimated_cost_usd == 0.0

    def test_total_cost(self) -> None:
        tracker = UsageTracker()
        tracker.record("s1", "gpt-4o", 1000, 500)
        tracker.record("s2", "gpt-4o", 1000, 500)
        assert tracker.get_total_cost() > 0

    def test_format_usage(self) -> None:
        tracker = UsageTracker()
        tracker.record("s1", "gpt-4o", 100, 50)
        formatted = tracker.format_usage("s1")
        assert "Turns: 1" in formatted
        assert "$" in formatted

    def test_format_no_data(self) -> None:
        tracker = UsageTracker()
        assert tracker.format_usage("nope") == "No usage data"
