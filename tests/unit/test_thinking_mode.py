"""Unit tests for thinking/reasoning mode."""

from __future__ import annotations

from vaultbot.llm.thinking import (
    ThinkingConfig,
    ThinkingStrategy,
    build_thinking_params,
    extract_thinking,
    should_use_thinking,
)


class TestShouldUseThinking:
    def test_always(self) -> None:
        config = ThinkingConfig(strategy=ThinkingStrategy.ALWAYS)
        assert should_use_thinking("simple", config) is True

    def test_never(self) -> None:
        config = ThinkingConfig(strategy=ThinkingStrategy.NEVER)
        assert should_use_thinking("analyze this", config) is False

    def test_auto_think_prefix(self) -> None:
        config = ThinkingConfig(strategy=ThinkingStrategy.AUTO)
        assert should_use_thinking("think: what is 2+2?", config) is True

    def test_auto_complexity_pattern(self) -> None:
        config = ThinkingConfig()
        assert should_use_thinking("analyze this code carefully", config) is True
        assert should_use_thinking("compare A and B", config) is True

    def test_auto_simple_query(self) -> None:
        config = ThinkingConfig()
        assert should_use_thinking("hello", config) is False

    def test_auto_long_query(self) -> None:
        config = ThinkingConfig()
        assert should_use_thinking("x " * 300, config) is True


class TestBuildThinkingParams:
    def test_claude(self) -> None:
        config = ThinkingConfig(budget_tokens=5000)
        params = build_thinking_params("claude", config)
        assert "thinking" in params

    def test_openai(self) -> None:
        params = build_thinking_params("openai", ThinkingConfig())
        assert params.get("reasoning_effort") == "high"

    def test_deepseek(self) -> None:
        params = build_thinking_params("deepseek", ThinkingConfig())
        assert params.get("model") == "deepseek-reasoner"

    def test_unknown_provider(self) -> None:
        params = build_thinking_params("unknown", ThinkingConfig())
        assert params == {}


class TestExtractThinking:
    def test_with_thinking_tags(self) -> None:
        text = "before <thinking>inner thought</thinking> after"
        result = extract_thinking(text)
        assert result.thinking == "inner thought"
        assert "inner thought" not in result.response

    def test_without_thinking_tags(self) -> None:
        text = "just a normal response"
        result = extract_thinking(text)
        assert result.thinking == ""
        assert result.response == text
