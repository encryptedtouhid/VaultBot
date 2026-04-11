"""Tests for conversation summarizer."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from vaultbot.core.message import ChatMessage
from vaultbot.core.summarizer import ConversationSummarizer
from vaultbot.llm.base import LLMChunk, LLMResponse, ToolDefinition


class MockLLMProvider:
    """Mock LLM that returns a fixed summary."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            content="User discussed weather and travel plans.",
            model="mock",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content="summary", is_final=True)


@pytest.fixture
def summarizer() -> ConversationSummarizer:
    return ConversationSummarizer(
        MockLLMProvider(),
        summary_threshold=5,
        keep_recent=3,
    )


@pytest.mark.asyncio
async def test_should_summarize_below_threshold(
    summarizer: ConversationSummarizer,
) -> None:
    assert await summarizer.should_summarize(3) is False


@pytest.mark.asyncio
async def test_should_summarize_above_threshold(
    summarizer: ConversationSummarizer,
) -> None:
    assert await summarizer.should_summarize(5) is True


@pytest.mark.asyncio
async def test_summarize_returns_summary(
    summarizer: ConversationSummarizer,
) -> None:
    messages = [
        ChatMessage(role="user", content=f"msg{i}")
        for i in range(10)
    ]
    summary = await summarizer.summarize(messages)
    assert "weather" in summary.lower()


@pytest.mark.asyncio
async def test_summarize_skips_when_few_messages(
    summarizer: ConversationSummarizer,
) -> None:
    messages = [ChatMessage(role="user", content="hello")]
    summary = await summarizer.summarize(messages, existing_summary="old")
    assert summary == "old"  # Returns existing, no new summary


def test_get_context_with_summary(
    summarizer: ConversationSummarizer,
) -> None:
    recent = [
        ChatMessage(role="user", content="hello"),
        ChatMessage(role="assistant", content="hi"),
    ]
    result = summarizer.get_context_with_summary(
        summary="User likes cats.",
        recent_messages=recent,
        system_prompt="Be helpful.",
    )
    assert result[0].role == "system"
    assert result[0].content == "Be helpful."
    assert "User likes cats" in result[1].content
    assert result[2].content == "hello"


def test_get_context_without_summary(
    summarizer: ConversationSummarizer,
) -> None:
    recent = [ChatMessage(role="user", content="hello")]
    result = summarizer.get_context_with_summary(
        summary="",
        recent_messages=recent,
    )
    assert len(result) == 1
    assert result[0].content == "hello"
