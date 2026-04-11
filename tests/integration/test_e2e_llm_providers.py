"""E2E integration tests for LLM provider factory and Gemini provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.core.message import ChatMessage
from vaultbot.llm.factory import create_provider


class TestE2EProviderFactory:
    """Test creating providers via factory and executing completions."""

    @pytest.mark.asyncio
    async def test_gemini_complete_pipeline(self) -> None:
        """Create Gemini via factory, mock API, get response."""
        provider = create_provider("gemini", api_key="test_key")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Gemini response"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3},
        }
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        result = await provider.complete(
            [
                ChatMessage(role="system", content="Be helpful."),
                ChatMessage(role="user", content="What is Python?"),
            ]
        )
        assert result.content == "Gemini response"
        assert result.input_tokens == 5

    @pytest.mark.asyncio
    async def test_deepseek_preset_complete(self) -> None:
        """Create DeepSeek via factory, verify preset config."""
        provider = create_provider("deepseek", api_key="test_key")
        assert provider.provider_name == "deepseek"
        assert "deepseek" in provider._base_url

    @pytest.mark.asyncio
    async def test_groq_preset_complete(self) -> None:
        """Create Groq via factory, verify preset config."""
        provider = create_provider("groq", api_key="test_key")
        assert provider.provider_name == "groq"
        assert "groq.com" in provider._base_url

    @pytest.mark.asyncio
    async def test_mistral_preset_complete(self) -> None:
        """Create Mistral via factory, verify preset config."""
        provider = create_provider("mistral", api_key="test_key")
        assert provider.provider_name == "mistral"
        assert "mistral.ai" in provider._base_url

    @pytest.mark.asyncio
    async def test_ollama_preset_complete(self) -> None:
        """Create Ollama via factory, verify preset config."""
        provider = create_provider("ollama")
        assert provider.provider_name == "ollama"
        assert "11434" in provider._base_url

    @pytest.mark.asyncio
    async def test_factory_to_complete_flow(self) -> None:
        """Full flow: factory -> provider -> complete with mock."""
        from vaultbot.llm.compatible import CompatibleProvider

        provider = CompatibleProvider.from_preset("deepseek", api_key="key")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "DeepSeek says hello"}, "finish_reason": "stop"}],
            "model": "deepseek-chat",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        result = await provider.complete([ChatMessage(role="user", content="hi")])
        assert result.content == "DeepSeek says hello"
        assert result.model == "deepseek-chat"

    @pytest.mark.asyncio
    async def test_all_compatible_providers_creatable(self) -> None:
        """All compatible presets can be instantiated via factory."""
        from vaultbot.llm.factory import _COMPATIBLE_PROVIDERS

        for name in _COMPATIBLE_PROVIDERS:
            provider = create_provider(name, api_key="test_key")
            assert provider.provider_name == name
