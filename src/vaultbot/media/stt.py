"""Speech-to-text engine with provider registry.

Supports multiple STT backends (OpenAI Whisper, Deepgram, local Whisper)
through a pluggable provider registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class AudioFormat(str, Enum):
    """Supported audio input formats."""

    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    FLAC = "flac"
    WEBM = "webm"
    M4A = "m4a"
    OPUS = "opus"
    AAC = "aac"


class TranscriptionMode(str, Enum):
    """Transcription processing modes."""

    BATCH = "batch"
    STREAMING = "streaming"


@dataclass(frozen=True, slots=True)
class STTRequest:
    """Parameters for an STT request."""

    audio_data: bytes
    format: AudioFormat = AudioFormat.WAV
    language: str = "auto"
    model: str = "whisper-1"
    mode: TranscriptionMode = TranscriptionMode.BATCH
    prompt: str = ""


@dataclass(frozen=True, slots=True)
class STTResult:
    """Result from an STT transcription request."""

    text: str
    language: str = ""
    provider: str = ""
    duration_seconds: float = 0.0
    confidence: float = 0.0
    segments: list[dict[str, object]] = field(default_factory=list)


@runtime_checkable
class STTProvider(Protocol):
    """Protocol for STT providers."""

    @property
    def provider_name(self) -> str: ...

    async def transcribe(self, request: STTRequest) -> STTResult: ...

    def supported_formats(self) -> list[AudioFormat]: ...


class STTEngine:
    """Orchestrates speech-to-text across multiple providers."""

    def __init__(self, default_provider: str = "") -> None:
        self._providers: dict[str, STTProvider] = {}
        self._default_provider = default_provider
        self._transcription_count: int = 0

    def register_provider(self, provider: STTProvider) -> None:
        self._providers[provider.provider_name] = provider
        if not self._default_provider:
            self._default_provider = provider.provider_name
        logger.info("stt_provider_registered", provider=provider.provider_name)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def supported_formats(self, provider: str | None = None) -> list[AudioFormat]:
        name = provider or self._default_provider
        if name and name in self._providers:
            return self._providers[name].supported_formats()
        return []

    async def transcribe(
        self,
        audio_data: bytes,
        *,
        provider: str | None = None,
        audio_format: AudioFormat = AudioFormat.WAV,
        language: str = "auto",
        model: str = "whisper-1",
        mode: TranscriptionMode = TranscriptionMode.BATCH,
        prompt: str = "",
    ) -> STTResult:
        provider_name = provider or self._default_provider
        if not provider_name or provider_name not in self._providers:
            available = ", ".join(self._providers.keys()) or "none"
            raise ValueError(f"Unknown STT provider '{provider_name}'. Available: {available}")

        stt_provider = self._providers[provider_name]
        request = STTRequest(
            audio_data=audio_data,
            format=audio_format,
            language=language,
            model=model,
            mode=mode,
            prompt=prompt,
        )

        logger.info(
            "stt_started",
            provider=provider_name,
            format=audio_format.value,
            audio_size=len(audio_data),
        )

        result = await stt_provider.transcribe(request)
        self._transcription_count += 1

        logger.info(
            "stt_completed",
            provider=provider_name,
            text_length=len(result.text),
            total=self._transcription_count,
        )
        return result

    @property
    def transcription_count(self) -> int:
        return self._transcription_count
