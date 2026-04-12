"""Unit tests for realtime voice and transcription."""

from __future__ import annotations

from vaultbot.media.realtime_transcription import (
    RealtimeTranscriptionProvider,
    RealtimeTranscriptionRegistry,
    TranscriptEvent,
    TranscriptType,
)
from vaultbot.media.realtime_voice import (
    RealtimeVoiceProvider,
    RealtimeVoiceRegistry,
    VoiceSession,
    VoiceSessionConfig,
    VoiceSessionState,
)


class MockVoiceProvider:
    @property
    def provider_name(self) -> str:
        return "mock_voice"

    async def connect(self, config: VoiceSessionConfig) -> VoiceSession:
        return VoiceSession(session_id="vs1", state=VoiceSessionState.ACTIVE, config=config)

    async def send_audio(self, session_id: str, audio_data: bytes) -> None:
        pass

    async def receive_audio(self, session_id: str) -> bytes:
        return b"\x00" * 100

    async def disconnect(self, session_id: str) -> None:
        pass


class MockTranscriptionProvider:
    @property
    def provider_name(self) -> str:
        return "mock_transcription"

    async def start(self, language: str, callback: object) -> str:
        return "ts1"

    async def send_audio(self, session_id: str, audio_data: bytes) -> None:
        pass

    async def stop(self, session_id: str) -> None:
        pass


class TestVoiceRegistry:
    def test_register_and_get(self) -> None:
        reg = RealtimeVoiceRegistry()
        reg.register(MockVoiceProvider())
        assert reg.get("mock_voice") is not None

    def test_get_default(self) -> None:
        reg = RealtimeVoiceRegistry()
        reg.register(MockVoiceProvider())
        assert reg.get() is not None

    def test_list_providers(self) -> None:
        reg = RealtimeVoiceRegistry()
        reg.register(MockVoiceProvider())
        assert "mock_voice" in reg.list_providers()

    def test_mock_is_provider(self) -> None:
        assert isinstance(MockVoiceProvider(), RealtimeVoiceProvider)


class TestTranscriptionRegistry:
    def test_register_and_get(self) -> None:
        reg = RealtimeTranscriptionRegistry()
        reg.register(MockTranscriptionProvider())
        assert reg.get("mock_transcription") is not None

    def test_list_providers(self) -> None:
        reg = RealtimeTranscriptionRegistry()
        reg.register(MockTranscriptionProvider())
        assert "mock_transcription" in reg.list_providers()

    def test_mock_is_provider(self) -> None:
        assert isinstance(MockTranscriptionProvider(), RealtimeTranscriptionProvider)


class TestTranscriptEvent:
    def test_partial(self) -> None:
        evt = TranscriptEvent(text="hello", transcript_type=TranscriptType.PARTIAL)
        assert evt.transcript_type == TranscriptType.PARTIAL

    def test_final(self) -> None:
        evt = TranscriptEvent(
            text="hello world", transcript_type=TranscriptType.FINAL, confidence=0.95
        )
        assert evt.confidence == 0.95

    def test_speech_start(self) -> None:
        evt = TranscriptEvent(text="", transcript_type=TranscriptType.PARTIAL, is_speech_start=True)
        assert evt.is_speech_start is True
