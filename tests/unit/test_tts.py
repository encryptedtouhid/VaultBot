"""Unit tests for TTS engine and providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.media.tts import (
    AudioFormat,
    TTSEngine,
    TTSProvider,
    TTSRequest,
    TTSResult,
    TTSVoice,
)


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockTTSProvider:
    def __init__(self, name: str = "mock_tts") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        return TTSResult(
            audio_data=b"fake_audio_data",
            format=request.format,
            provider=self._name,
            voice=request.voice,
            duration_seconds=1.5,
        )

    def list_voices(self) -> list[str]:
        return ["alloy", "echo", "nova"]


# ---------------------------------------------------------------------------
# Base types
# ---------------------------------------------------------------------------


class TestTTSBaseTypes:
    def test_audio_format_enum(self) -> None:
        assert AudioFormat.MP3.value == "mp3"
        assert AudioFormat.OPUS.value == "opus"

    def test_tts_voice_enum(self) -> None:
        assert TTSVoice.ALLOY.value == "alloy"

    def test_request_defaults(self) -> None:
        req = TTSRequest(text="hello")
        assert req.voice == "alloy"
        assert req.model == "tts-1"
        assert req.format == AudioFormat.MP3
        assert req.speed == 1.0

    def test_result_dataclass(self) -> None:
        result = TTSResult(audio_data=b"data", format=AudioFormat.MP3, provider="test", voice="alloy")
        assert result.audio_data == b"data"
        assert result.duration_seconds == 0.0

    def test_mock_is_tts_provider(self) -> None:
        assert isinstance(MockTTSProvider(), TTSProvider)


# ---------------------------------------------------------------------------
# TTS Engine
# ---------------------------------------------------------------------------


class TestTTSEngine:
    def test_register_provider(self) -> None:
        engine = TTSEngine()
        engine.register_provider(MockTTSProvider("openai_tts"))
        assert "openai_tts" in engine.list_providers()

    def test_first_registered_is_default(self) -> None:
        engine = TTSEngine()
        engine.register_provider(MockTTSProvider("first"))
        engine.register_provider(MockTTSProvider("second"))
        assert engine._default_provider == "first"

    def test_list_voices(self) -> None:
        engine = TTSEngine()
        engine.register_provider(MockTTSProvider("test"))
        voices = engine.list_voices()
        assert "alloy" in voices

    def test_list_voices_empty_no_providers(self) -> None:
        engine = TTSEngine()
        assert engine.list_voices() == []

    @pytest.mark.asyncio
    async def test_synthesize_success(self) -> None:
        engine = TTSEngine()
        engine.register_provider(MockTTSProvider("test"))

        result = await engine.synthesize("hello world")
        assert result.audio_data == b"fake_audio_data"
        assert result.provider == "test"
        assert engine.synthesis_count == 1

    @pytest.mark.asyncio
    async def test_synthesize_with_specific_provider(self) -> None:
        engine = TTSEngine()
        engine.register_provider(MockTTSProvider("a"))
        engine.register_provider(MockTTSProvider("b"))

        result = await engine.synthesize("test", provider="b")
        assert result.provider == "b"

    @pytest.mark.asyncio
    async def test_synthesize_unknown_provider_raises(self) -> None:
        engine = TTSEngine()
        engine.register_provider(MockTTSProvider("a"))

        with pytest.raises(ValueError, match="Unknown TTS provider"):
            await engine.synthesize("test", provider="nonexistent")

    @pytest.mark.asyncio
    async def test_synthesize_no_providers_raises(self) -> None:
        engine = TTSEngine()
        with pytest.raises(ValueError):
            await engine.synthesize("test")

    @pytest.mark.asyncio
    async def test_synthesize_with_options(self) -> None:
        engine = TTSEngine()
        engine.register_provider(MockTTSProvider("test"))

        result = await engine.synthesize(
            "hello", voice="nova", format=AudioFormat.OPUS, speed=1.5
        )
        assert result.voice == "nova"
        assert result.format == AudioFormat.OPUS

    @pytest.mark.asyncio
    async def test_synthesis_count_increments(self) -> None:
        engine = TTSEngine()
        engine.register_provider(MockTTSProvider("test"))
        await engine.synthesize("a")
        await engine.synthesize("b")
        assert engine.synthesis_count == 2


# ---------------------------------------------------------------------------
# OpenAI TTS Provider
# ---------------------------------------------------------------------------


class TestOpenAITTSProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.openai_tts import OpenAITTSProvider
        provider = OpenAITTSProvider(api_key="test")
        assert provider.provider_name == "openai_tts"

    def test_list_voices(self) -> None:
        from vaultbot.media.providers.openai_tts import OpenAITTSProvider
        provider = OpenAITTSProvider(api_key="test")
        voices = provider.list_voices()
        assert "alloy" in voices
        assert "shimmer" in voices

    @pytest.mark.asyncio
    async def test_synthesize_calls_api(self) -> None:
        from vaultbot.media.providers.openai_tts import OpenAITTSProvider
        provider = OpenAITTSProvider(api_key="test")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = b"audio_bytes_here"
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        req = TTSRequest(text="hello world")
        result = await provider.synthesize(req)

        assert result.audio_data == b"audio_bytes_here"
        assert result.provider == "openai_tts"
        provider._client.post.assert_called_once()


# ---------------------------------------------------------------------------
# ElevenLabs Provider
# ---------------------------------------------------------------------------


class TestElevenLabsProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.elevenlabs import ElevenLabsProvider
        provider = ElevenLabsProvider(api_key="test")
        assert provider.provider_name == "elevenlabs"

    def test_list_voices(self) -> None:
        from vaultbot.media.providers.elevenlabs import ElevenLabsProvider
        provider = ElevenLabsProvider(api_key="test")
        voices = provider.list_voices()
        assert "rachel" in voices
        assert "sarah" in voices

    @pytest.mark.asyncio
    async def test_synthesize_calls_api(self) -> None:
        from vaultbot.media.providers.elevenlabs import ElevenLabsProvider
        provider = ElevenLabsProvider(api_key="test")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = b"elevenlabs_audio"
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        req = TTSRequest(text="hello", voice="rachel")
        result = await provider.synthesize(req)

        assert result.audio_data == b"elevenlabs_audio"
        assert result.provider == "elevenlabs"
        assert result.format == AudioFormat.MP3
