"""Unit tests for context compaction."""

from __future__ import annotations

import pytest

from vaultbot.core.compaction import (
    ContextCompactor,
    TokenBudget,
    estimate_messages_tokens,
    estimate_tokens,
)
from vaultbot.core.message import ChatMessage


class TestEstimateTokens:
    def test_empty_string(self) -> None:
        assert estimate_tokens("") == 1  # Minimum 1

    def test_short_text(self) -> None:
        assert estimate_tokens("hello") >= 1

    def test_long_text(self) -> None:
        text = "a" * 400
        assert estimate_tokens(text) == 100

    def test_messages(self) -> None:
        msgs = [
            ChatMessage(role="user", content="hello"),
            ChatMessage(role="assistant", content="hi there"),
        ]
        tokens = estimate_messages_tokens(msgs)
        assert tokens > 0


class TestTokenBudget:
    def test_defaults(self) -> None:
        budget = TokenBudget()
        assert budget.total == 128_000
        assert budget.available_for_history > 0

    def test_custom_budget(self) -> None:
        budget = TokenBudget(total=10_000, system_prompt=500, tools=500, response=500, compaction_summary=500)
        assert budget.available_for_history == 8_000


class TestContextCompactor:
    def test_no_compaction_needed(self) -> None:
        compactor = ContextCompactor()
        msgs = [
            ChatMessage(role="user", content="hello"),
            ChatMessage(role="assistant", content="hi"),
        ]
        result = compactor.compact(msgs)
        assert result == msgs  # No change
        assert compactor.compaction_count == 0

    def test_compaction_triggered(self) -> None:
        # Create a very small budget to force compaction
        budget = TokenBudget(total=100, system_prompt=10, tools=10, response=10, compaction_summary=10)
        compactor = ContextCompactor(budget=budget, preserve_recent=2)

        msgs = [
            ChatMessage(role="user", content="message " * 50),
            ChatMessage(role="assistant", content="response " * 50),
            ChatMessage(role="user", content="message 2 " * 50),
            ChatMessage(role="assistant", content="response 2 " * 50),
            ChatMessage(role="user", content="recent 1"),
            ChatMessage(role="assistant", content="recent 2"),
        ]

        result = compactor.compact(msgs)
        assert len(result) < len(msgs)
        assert compactor.compaction_count == 1

        # Recent messages should be preserved
        assert result[-1].content == "recent 2"
        assert result[-2].content == "recent 1"

    def test_compaction_preserves_system_messages(self) -> None:
        budget = TokenBudget(total=100, system_prompt=10, tools=10, response=10, compaction_summary=10)
        compactor = ContextCompactor(budget=budget, preserve_recent=1)

        msgs = [
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="old message " * 50),
            ChatMessage(role="assistant", content="old response " * 50),
            ChatMessage(role="user", content="recent"),
        ]

        result = compactor.compact(msgs)
        # System message should still be present
        system_msgs = [m for m in result if m.role == "system"]
        assert len(system_msgs) >= 1

    def test_summary_includes_topics(self) -> None:
        summary = ContextCompactor._summarize_messages([
            ChatMessage(role="user", content="Tell me about Python programming"),
            ChatMessage(role="assistant", content="Python is a versatile language."),
            ChatMessage(role="user", content="What about JavaScript?"),
        ])
        assert "Topics discussed" in summary
        assert "Python" in summary

    def test_summary_includes_message_count(self) -> None:
        summary = ContextCompactor._summarize_messages([
            ChatMessage(role="user", content="msg1"),
            ChatMessage(role="user", content="msg2"),
        ])
        assert "2" in summary

    def test_no_old_messages_no_compaction(self) -> None:
        budget = TokenBudget(total=50, system_prompt=5, tools=5, response=5, compaction_summary=5)
        compactor = ContextCompactor(budget=budget, preserve_recent=10)

        msgs = [ChatMessage(role="user", content="x" * 200)]
        result = compactor.compact(msgs)
        # Only one message, nothing old to compact
        assert result == msgs

    def test_multiple_compactions(self) -> None:
        budget = TokenBudget(total=50, system_prompt=5, tools=5, response=5, compaction_summary=5)
        compactor = ContextCompactor(budget=budget, preserve_recent=1)

        for _ in range(3):
            msgs = [
                ChatMessage(role="user", content="old message content " * 100),
                ChatMessage(role="assistant", content="old response content " * 100),
                ChatMessage(role="user", content="recent"),
            ]
            compactor.compact(msgs)

        assert compactor.compaction_count == 3
