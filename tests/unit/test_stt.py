"""Unit tests for STT engine, providers, VAD, and audio pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.media.stt import (
    AudioFormat,
    STTEngine,
    STTProvider,
    STTRequest,
    STTResult,
    TranscriptionMode,
)


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockSTTProvider:
    def __init__(self, name: str = "mock_stt") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def transcribe(self, request: STTRequest) -> STTResult:
        return STTResult(
            text="hello world",
            language="en",
            provider=self._name,
            duration_seconds=2.5,
            confidence=0.95,
        )

    def supported_formats(self) -> list[AudioFormat]:
        return [AudioFormat.WAV, AudioFormat.MP3]


# ---------------------------------------------------------------------------
# Base types
# ---------------------------------------------------------------------------


class TestSTTBaseTypes:
    def test_audio_format_enum(self) -> None:
        assert AudioFormat.WAV.value == "wav"
        assert AudioFormat.MP3.value == "mp3"

    def test_transcription_mode_enum(self) -> None:
        assert TranscriptionMode.BATCH.value == "batch"
        assert TranscriptionMode.STREAMING.value == "streaming"

    def test_request_defaults(self) -> None:
        req = STTRequest(audio_data=b"data")
        assert req.format == AudioFormat.WAV
        assert req.language == "auto"
        assert req.model == "whisper-1"
        assert req.mode == TranscriptionMode.BATCH

    def test_result_dataclass(self) -> None:
        result = STTResult(text="hello", provider="test")
        assert result.text == "hello"
        assert result.duration_seconds == 0.0
        assert result.confidence == 0.0
        assert result.segments == []

    def test_mock_is_stt_provider(self) -> None:
        assert isinstance(MockSTTProvider(), STTProvider)


# ---------------------------------------------------------------------------
# STT Engine
# ---------------------------------------------------------------------------


class TestSTTEngine:
    def test_register_provider(self) -> None:
        engine = STTEngine()
        engine.register_provider(MockSTTProvider("whisper"))
        assert "whisper" in engine.list_providers()

    def test_first_registered_is_default(self) -> None:
        engine = STTEngine()
        engine.register_provider(MockSTTProvider("first"))
        engine.register_provider(MockSTTProvider("second"))
        assert engine._default_provider == "first"

    def test_supported_formats(self) -> None:
        engine = STTEngine()
        engine.register_provider(MockSTTProvider("test"))
        formats = engine.supported_formats()
        assert AudioFormat.WAV in formats

    def test_supported_formats_empty(self) -> None:
        engine = STTEngine()
        assert engine.supported_formats() == []

    @pytest.mark.asyncio
    async def test_transcribe_success(self) -> None:
        engine = STTEngine()
        engine.register_provider(MockSTTProvider("test"))
        result = await engine.transcribe(b"audio_data")
        assert result.text == "hello world"
        assert result.provider == "test"
        assert engine.transcription_count == 1

    @pytest.mark.asyncio
    async def test_transcribe_specific_provider(self) -> None:
        engine = STTEngine()
        engine.register_provider(MockSTTProvider("a"))
        engine.register_provider(MockSTTProvider("b"))
        result = await engine.transcribe(b"data", provider="b")
        assert result.provider == "b"

    @pytest.mark.asyncio
    async def test_transcribe_unknown_provider_raises(self) -> None:
        engine = STTEngine()
        engine.register_provider(MockSTTProvider("a"))
        with pytest.raises(ValueError, match="Unknown STT provider"):
            await engine.transcribe(b"data", provider="nonexistent")

    @pytest.mark.asyncio
    async def test_transcribe_no_providers_raises(self) -> None:
        engine = STTEngine()
        with pytest.raises(ValueError, match="Unknown STT provider"):
            await engine.transcribe(b"data")

    @pytest.mark.asyncio
    async def test_transcription_count_increments(self) -> None:
        engine = STTEngine()
        engine.register_provider(MockSTTProvider("test"))
        await engine.transcribe(b"a")
        await engine.transcribe(b"b")
        assert engine.transcription_count == 2


# ---------------------------------------------------------------------------
# Whisper API Provider
# ---------------------------------------------------------------------------


class TestWhisperAPIProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.whisper_api import WhisperAPIProvider

        provider = WhisperAPIProvider(api_key="test")
        assert provider.provider_name == "whisper_api"

    def test_supported_formats(self) -> None:
        from vaultbot.media.providers.whisper_api import WhisperAPIProvider

        provider = WhisperAPIProvider(api_key="test")
        formats = provider.supported_formats()
        assert AudioFormat.WAV in formats
        assert AudioFormat.MP3 in formats

    @pytest.mark.asyncio
    async def test_transcribe_calls_api(self) -> None:
        from vaultbot.media.providers.whisper_api import WhisperAPIProvider

        provider = WhisperAPIProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={
            "text": "hello world",
            "language": "en",
            "duration": 2.5,
            "segments": [],
        })
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        req = STTRequest(audio_data=b"fake_audio")
        result = await provider.transcribe(req)
        assert result.text == "hello world"
        assert result.provider == "whisper_api"
        provider._client.post.assert_called_once()


# ---------------------------------------------------------------------------
# Deepgram Provider
# ---------------------------------------------------------------------------


class TestDeepgramProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.deepgram import DeepgramProvider

        provider = DeepgramProvider(api_key="test")
        assert provider.provider_name == "deepgram"

    def test_supported_formats(self) -> None:
        from vaultbot.media.providers.deepgram import DeepgramProvider

        provider = DeepgramProvider(api_key="test")
        formats = provider.supported_formats()
        assert AudioFormat.WAV in formats

    @pytest.mark.asyncio
    async def test_transcribe_calls_api(self) -> None:
        from vaultbot.media.providers.deepgram import DeepgramProvider

        provider = DeepgramProvider(api_key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={
            "results": {
                "channels": [{
                    "alternatives": [{"transcript": "hello", "confidence": 0.98}],
                    "detected_language": "en",
                }],
            },
            "metadata": {"duration": 1.5},
        })
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        req = STTRequest(audio_data=b"audio")
        result = await provider.transcribe(req)
        assert result.text == "hello"
        assert result.provider == "deepgram"
        assert result.confidence == 0.98


# ---------------------------------------------------------------------------
# Local Whisper Provider
# ---------------------------------------------------------------------------


class TestLocalWhisperProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.local_whisper import LocalWhisperProvider

        provider = LocalWhisperProvider.__new__(LocalWhisperProvider)
        provider._model_size = "base"
        provider._model = None
        assert provider.provider_name == "local_whisper"

    def test_supported_formats(self) -> None:
        from vaultbot.media.providers.local_whisper import LocalWhisperProvider

        provider = LocalWhisperProvider.__new__(LocalWhisperProvider)
        provider._model_size = "base"
        provider._model = None
        formats = provider.supported_formats()
        assert AudioFormat.WAV in formats

    @pytest.mark.asyncio
    async def test_transcribe_no_model_raises(self) -> None:
        from vaultbot.media.providers.local_whisper import LocalWhisperProvider

        provider = LocalWhisperProvider.__new__(LocalWhisperProvider)
        provider._model_size = "base"
        provider._model = None

        req = STTRequest(audio_data=b"audio")
        with pytest.raises(RuntimeError, match="not available"):
            await provider.transcribe(req)


# ---------------------------------------------------------------------------
# VAD Engine
# ---------------------------------------------------------------------------


class TestVADEngine:
    def test_initial_state(self) -> None:
        from vaultbot.media.vad import VADEngine, VADState

        engine = VADEngine()
        assert engine.state == VADState.SILENCE

    def test_config_defaults(self) -> None:
        from vaultbot.media.vad import VADConfig, VADEngine

        engine = VADEngine()
        assert engine.config.sensitivity == 0.5
        assert engine.config.silence_threshold_ms == 1500

    def test_custom_config(self) -> None:
        from vaultbot.media.vad import VADConfig, VADEngine

        config = VADConfig(sensitivity=0.3, silence_threshold_ms=1000)
        engine = VADEngine(config=config)
        assert engine.config.sensitivity == 0.3

    def test_reset(self) -> None:
        from vaultbot.media.vad import VADEngine, VADState

        engine = VADEngine()
        engine._state = VADState.SPEECH
        engine.reset()
        assert engine.state == VADState.SILENCE

    def test_detect_segments_empty(self) -> None:
        from vaultbot.media.vad import VADEngine

        engine = VADEngine()
        segments = engine.detect_segments(b"")
        assert segments == []

    def test_detect_segments_silence(self) -> None:
        from vaultbot.media.vad import VADEngine

        engine = VADEngine()
        silent_audio = b"\x00\x00" * 16000  # 1 second of silence
        segments = engine.detect_segments(silent_audio)
        assert segments == []


# ---------------------------------------------------------------------------
# Audio Pipeline
# ---------------------------------------------------------------------------


class TestAudioPipeline:
    def test_detect_format_wav(self) -> None:
        from vaultbot.media.audio_pipeline import AudioPipeline

        pipeline = AudioPipeline()
        fmt = pipeline.detect_format(b"RIFF" + b"\x00" * 100)
        assert fmt == AudioFormat.WAV

    def test_detect_format_mp3(self) -> None:
        from vaultbot.media.audio_pipeline import AudioPipeline

        pipeline = AudioPipeline()
        fmt = pipeline.detect_format(b"ID3" + b"\x00" * 100)
        assert fmt == AudioFormat.MP3

    def test_detect_format_flac(self) -> None:
        from vaultbot.media.audio_pipeline import AudioPipeline

        pipeline = AudioPipeline()
        fmt = pipeline.detect_format(b"fLaC" + b"\x00" * 100)
        assert fmt == AudioFormat.FLAC

    def test_validate_empty_raises(self) -> None:
        from vaultbot.media.audio_pipeline import AudioPipeline, AudioValidationError

        pipeline = AudioPipeline()
        with pytest.raises(AudioValidationError, match="Empty"):
            pipeline.validate(b"")

    def test_validate_too_large_raises(self) -> None:
        from vaultbot.media.audio_pipeline import AudioPipeline, AudioPipelineConfig, AudioValidationError

        config = AudioPipelineConfig(max_size_bytes=100)
        pipeline = AudioPipeline(config=config)
        with pytest.raises(AudioValidationError, match="exceeds max"):
            pipeline.validate(b"\x00" * 200)

    def test_validate_success(self) -> None:
        from vaultbot.media.audio_pipeline import AudioPipeline

        pipeline = AudioPipeline()
        metadata = pipeline.validate(b"RIFF" + b"\x00" * 100)
        assert metadata.format == AudioFormat.WAV
        assert metadata.size_bytes == 104

    def test_normalize(self) -> None:
        from vaultbot.media.audio_pipeline import AudioPipeline

        pipeline = AudioPipeline()
        data = b"RIFF" + b"\x00" * 100
        normalized, metadata = pipeline.normalize(data)
        assert normalized == data
        assert metadata.format == AudioFormat.WAV
