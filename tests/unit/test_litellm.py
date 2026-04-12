"""Unit tests for LiteLLM proxy integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMProvider
from vaultbot.llm.litellm_proxy import LiteLLMConfig, LiteLLMProxyProvider


class TestLiteLLMConfig:
    def test_defaults(self) -> None:
        config = LiteLLMConfig()
        assert config.proxy_url == "http://localhost:4000"
        assert config.default_model == "gpt-4o"

    def test_resolve_model_alias(self) -> None:
        config = LiteLLMConfig(model_aliases={"fast": "gpt-4o-mini"})
        assert config.resolve_model("fast") == "gpt-4o-mini"

    def test_resolve_model_passthrough(self) -> None:
        config = LiteLLMConfig()
        assert config.resolve_model("claude-3") == "claude-3"


class TestLiteLLMProxyProvider:
    def test_provider_name(self) -> None:
        p = LiteLLMProxyProvider()
        assert p.provider_name == "litellm"

    def test_is_llm_provider(self) -> None:
        p = LiteLLMProxyProvider()
        assert isinstance(p, LLMProvider)

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        p = LiteLLMProxyProvider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(
            return_value={
                "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 1},
                "model": "gpt-4o",
            }
        )
        p._inner._client = AsyncMock()
        p._inner._client.post = AsyncMock(return_value=mock_resp)
        result = await p.complete([ChatMessage(role="user", content="hello")])
        assert result.content == "hi"

    def test_config_accessible(self) -> None:
        config = LiteLLMConfig(api_key="test-key")
        p = LiteLLMProxyProvider(config)
        assert p.config.api_key == "test-key"
