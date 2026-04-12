"""Unit tests for Asian LLM providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMProvider


class TestQwenProvider:
    def test_provider_name(self) -> None:
        from vaultbot.llm.qwen import QwenProvider
        p = QwenProvider(api_key="test")
        assert p.provider_name == "qwen"

    def test_is_llm_provider(self) -> None:
        from vaultbot.llm.qwen import QwenProvider
        p = QwenProvider(api_key="test")
        assert isinstance(p, LLMProvider)

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        from vaultbot.llm.qwen import QwenProvider
        p = QwenProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={
            "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
            "model": "qwen-max",
        })
        p._inner._client = AsyncMock()
        p._inner._client.post = AsyncMock(return_value=mock_resp)
        result = await p.complete([ChatMessage(role="user", content="hello")])
        assert result.content == "hi"


class TestDeepSeekProvider:
    def test_provider_name(self) -> None:
        from vaultbot.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="test")
        assert p.provider_name == "deepseek"

    def test_is_llm_provider(self) -> None:
        from vaultbot.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="test")
        assert isinstance(p, LLMProvider)

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        from vaultbot.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={
            "choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            "model": "deepseek-chat",
        })
        p._inner._client = AsyncMock()
        p._inner._client.post = AsyncMock(return_value=mock_resp)
        result = await p.complete([ChatMessage(role="user", content="test")])
        assert result.content == "answer"


class TestZhipuProvider:
    def test_provider_name(self) -> None:
        from vaultbot.llm.zhipu import ZhipuProvider
        p = ZhipuProvider(api_key="test")
        assert p.provider_name == "zhipu"

    def test_is_llm_provider(self) -> None:
        from vaultbot.llm.zhipu import ZhipuProvider
        p = ZhipuProvider(api_key="test")
        assert isinstance(p, LLMProvider)

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        from vaultbot.llm.zhipu import ZhipuProvider
        p = ZhipuProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={
            "choices": [{"message": {"content": "reply"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1},
            "model": "glm-4",
        })
        p._inner._client = AsyncMock()
        p._inner._client.post = AsyncMock(return_value=mock_resp)
        result = await p.complete([ChatMessage(role="user", content="hi")])
        assert result.content == "reply"


class TestMoonshotProvider:
    def test_provider_name(self) -> None:
        from vaultbot.llm.moonshot import MoonshotProvider
        p = MoonshotProvider(api_key="test")
        assert p.provider_name == "moonshot"

    def test_is_llm_provider(self) -> None:
        from vaultbot.llm.moonshot import MoonshotProvider
        p = MoonshotProvider(api_key="test")
        assert isinstance(p, LLMProvider)

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        from vaultbot.llm.moonshot import MoonshotProvider
        p = MoonshotProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={
            "choices": [{"message": {"content": "kimi says hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 3},
            "model": "moonshot-v1-8k",
        })
        p._inner._client = AsyncMock()
        p._inner._client.post = AsyncMock(return_value=mock_resp)
        result = await p.complete([ChatMessage(role="user", content="hey")])
        assert result.content == "kimi says hi"
