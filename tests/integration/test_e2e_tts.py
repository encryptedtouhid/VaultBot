"""E2E integration tests for TTS pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.media.tts import AudioFormat, TTSEngine, TTSRequest, TTSResult


class TestE2ETTS:
    @pytest.mark.asyncio
    async def test_openai_tts_full_pipeline(self) -> None:
        from vaultbot.media.providers.openai_tts import OpenAITTSProvider

        engine = TTSEngine()

        provider = OpenAITTSProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = b"generated_speech_audio"
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        engine.register_provider(provider)

        result = await engine.synthesize("Hello, this is VaultBot speaking.", voice="nova")
        assert result.audio_data == b"generated_speech_audio"
        assert result.provider == "openai_tts"
        assert engine.synthesis_count == 1

    @pytest.mark.asyncio
    async def test_elevenlabs_full_pipeline(self) -> None:
        from vaultbot.media.providers.elevenlabs import ElevenLabsProvider

        engine = TTSEngine()

        provider = ElevenLabsProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = b"elevenlabs_speech"
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        engine.register_provider(provider)

        result = await engine.synthesize("Hello from ElevenLabs", voice="rachel")
        assert result.audio_data == b"elevenlabs_speech"
        assert result.provider == "elevenlabs"

    @pytest.mark.asyncio
    async def test_multi_provider_tts(self) -> None:
        engine = TTSEngine()

        class FakeTTS:
            def __init__(self, name: str) -> None:
                self._name = name

            @property
            def provider_name(self) -> str:
                return self._name

            async def synthesize(self, request: TTSRequest) -> TTSResult:
                return TTSResult(
                    audio_data=b"audio",
                    format=AudioFormat.MP3,
                    provider=self._name,
                    voice=request.voice,
                )

            def list_voices(self) -> list[str]:
                return ["default"]

        engine.register_provider(FakeTTS("tts_a"))
        engine.register_provider(FakeTTS("tts_b"))

        r1 = await engine.synthesize("test", provider="tts_a")
        assert r1.provider == "tts_a"

        r2 = await engine.synthesize("test", provider="tts_b")
        assert r2.provider == "tts_b"

        assert engine.synthesis_count == 2
