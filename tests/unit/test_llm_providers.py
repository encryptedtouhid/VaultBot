"""Unit tests for LLM providers: Gemini, factory, and enhanced compatible presets."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMProvider

# ==========================================================================
# Gemini Provider
# ==========================================================================


class TestGeminiProviderInit:
    def test_provider_name(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        provider = GeminiProvider(api_key="test_key")
        assert provider.provider_name == "gemini"

    def test_default_model(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        provider = GeminiProvider(api_key="test_key")
        assert provider._default_model == "gemini-2.0-flash"

    def test_custom_model(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        provider = GeminiProvider(api_key="test_key", default_model="gemini-1.5-pro")
        assert provider._default_model == "gemini-1.5-pro"


class TestGeminiMessageConversion:
    def test_user_message(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        messages = [ChatMessage(role="user", content="hello")]
        contents = GeminiProvider._convert_messages(messages)
        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "hello"

    def test_assistant_maps_to_model(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        messages = [
            ChatMessage(role="user", content="hi"),
            ChatMessage(role="assistant", content="hello"),
        ]
        contents = GeminiProvider._convert_messages(messages)
        assert contents[1]["role"] == "model"

    def test_system_prepended_to_first_user(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        messages = [
            ChatMessage(role="system", content="You are helpful."),
            ChatMessage(role="user", content="hi"),
        ]
        contents = GeminiProvider._convert_messages(messages)
        assert len(contents) == 1  # System merged into user
        assert "You are helpful." in contents[0]["parts"][0]["text"]
        assert "hi" in contents[0]["parts"][0]["text"]

    def test_empty_messages(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        contents = GeminiProvider._convert_messages([])
        assert contents == []


class TestGeminiComplete:
    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        provider = GeminiProvider(api_key="test_key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Hello there!"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 5,
            },
        }

        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        result = await provider.complete([ChatMessage(role="user", content="hi")])
        assert result.content == "Hello there!"
        assert result.input_tokens == 10
        assert result.output_tokens == 5

    @pytest.mark.asyncio
    async def test_complete_no_candidates_raises(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        provider = GeminiProvider(api_key="test_key")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"candidates": []}

        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(RuntimeError, match="no candidates"):
            await provider.complete([ChatMessage(role="user", content="hi")])


class TestGeminiClose:
    @pytest.mark.asyncio
    async def test_close(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        provider = GeminiProvider(api_key="test_key")
        provider._client = AsyncMock()
        await provider.close()
        provider._client.aclose.assert_called_once()


# ==========================================================================
# Compatible Provider - New Presets
# ==========================================================================


class TestCompatiblePresets:
    def test_xai_preset_exists(self) -> None:
        from vaultbot.llm.compatible import PROVIDER_PRESETS

        assert "xai" in PROVIDER_PRESETS
        assert "x.ai" in PROVIDER_PRESETS["xai"]["base_url"]

    def test_bedrock_compat_preset_exists(self) -> None:
        from vaultbot.llm.compatible import PROVIDER_PRESETS

        assert "bedrock_compat" in PROVIDER_PRESETS

    def test_deepseek_preset(self) -> None:
        from vaultbot.llm.compatible import PROVIDER_PRESETS

        assert "deepseek" in PROVIDER_PRESETS
        assert "deepseek" in PROVIDER_PRESETS["deepseek"]["base_url"]

    def test_groq_preset(self) -> None:
        from vaultbot.llm.compatible import PROVIDER_PRESETS

        assert "groq" in PROVIDER_PRESETS
        assert "groq.com" in PROVIDER_PRESETS["groq"]["base_url"]

    def test_mistral_preset(self) -> None:
        from vaultbot.llm.compatible import PROVIDER_PRESETS

        assert "mistral" in PROVIDER_PRESETS
        assert "mistral.ai" in PROVIDER_PRESETS["mistral"]["base_url"]

    def test_ollama_preset(self) -> None:
        from vaultbot.llm.compatible import PROVIDER_PRESETS

        assert "ollama" in PROVIDER_PRESETS
        assert "11434" in PROVIDER_PRESETS["ollama"]["base_url"]

    def test_from_preset_creates_provider(self) -> None:
        from vaultbot.llm.compatible import CompatibleProvider

        provider = CompatibleProvider.from_preset("deepseek", api_key="test_key")
        assert provider.provider_name == "deepseek"

    def test_from_preset_unknown_raises(self) -> None:
        from vaultbot.llm.compatible import CompatibleProvider

        with pytest.raises(ValueError, match="Unknown preset"):
            CompatibleProvider.from_preset("nonexistent")

    def test_from_preset_model_override(self) -> None:
        from vaultbot.llm.compatible import CompatibleProvider

        provider = CompatibleProvider.from_preset("groq", api_key="key", model="custom-model")
        assert provider._default_model == "custom-model"

    def test_all_presets_have_required_fields(self) -> None:
        from vaultbot.llm.compatible import PROVIDER_PRESETS

        for name, preset in PROVIDER_PRESETS.items():
            assert "base_url" in preset, f"{name} missing base_url"
            assert "default_model" in preset, f"{name} missing default_model"
            assert "name" in preset, f"{name} missing name"


# ==========================================================================
# Provider Factory
# ==========================================================================


class TestProviderFactory:
    def test_create_claude(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("claude", api_key="test_key")
        assert provider.provider_name == "claude"

    def test_create_openai(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("openai", api_key="test_key")
        assert provider.provider_name == "openai"

    def test_create_gemini(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("gemini", api_key="test_key")
        assert provider.provider_name == "gemini"

    def test_create_deepseek(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("deepseek", api_key="test_key")
        assert provider.provider_name == "deepseek"

    def test_create_groq(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("groq", api_key="test_key")
        assert provider.provider_name == "groq"

    def test_create_mistral(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("mistral", api_key="test_key")
        assert provider.provider_name == "mistral"

    def test_create_ollama(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("ollama", api_key="not-needed")
        assert provider.provider_name == "ollama"

    def test_create_xai(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("xai", api_key="test_key")
        assert provider.provider_name == "xai"

    def test_create_local(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("local")
        assert provider.provider_name == "local"

    def test_create_custom_with_base_url(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("my_custom", api_key="key", base_url="http://localhost:9999/v1")
        assert provider.provider_name == "my_custom"

    def test_create_unknown_without_base_url_raises(self) -> None:
        from vaultbot.llm.factory import create_provider

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_provider("nonexistent_provider")

    def test_case_insensitive(self) -> None:
        from vaultbot.llm.factory import create_provider

        provider = create_provider("DeepSeek", api_key="test_key")
        assert provider.provider_name == "deepseek"

    def test_list_providers(self) -> None:
        from vaultbot.llm.factory import list_providers

        providers = list_providers()
        assert "claude" in providers
        assert "gemini" in providers
        assert "deepseek" in providers
        assert "groq" in providers
        assert "mistral" in providers
        assert "ollama" in providers
        assert "xai" in providers
        assert len(providers) >= 14


# ==========================================================================
# Protocol compliance
# ==========================================================================


class TestProtocolCompliance:
    def test_gemini_is_llm_provider(self) -> None:
        from vaultbot.llm.gemini import GeminiProvider

        provider = GeminiProvider(api_key="test")
        assert isinstance(provider, LLMProvider)
