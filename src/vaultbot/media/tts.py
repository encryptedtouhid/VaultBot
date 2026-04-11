"""Text-to-speech engine with provider registry.

Supports multiple TTS backends (OpenAI TTS, ElevenLabs) through a
pluggable provider registry.  Generated audio can be delivered as
voice messages on platforms that support them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class AudioFormat(str, Enum):
    """Supported audio output formats."""
    MP3 = "mp3"
    OPUS = "opus"
    AAC = "aac"
    FLAC = "flac"
    WAV = "wav"
    PCM = "pcm"


class TTSVoice(str, Enum):
    """Standard voice presets (OpenAI compatible)."""
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


@dataclass(frozen=True, slots=True)
class TTSRequest:
    """Parameters for a TTS request."""
    text: str
    voice: str = "alloy"
    model: str = "tts-1"
    format: AudioFormat = AudioFormat.MP3
    speed: float = 1.0


@dataclass(frozen=True, slots=True)
class TTSResult:
    """Result from a TTS generation request."""
    audio_data: bytes
    format: AudioFormat
    provider: str
    voice: str
    duration_seconds: float = 0.0


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol for TTS providers."""

    @property
    def provider_name(self) -> str: ...

    async def synthesize(self, request: TTSRequest) -> TTSResult: ...

    def list_voices(self) -> list[str]: ...


class TTSEngine:
    """Orchestrates text-to-speech across multiple providers.

    Parameters
    ----------
    default_provider:
        Name of the default provider.
    """

    def __init__(self, default_provider: str = "") -> None:
        self._providers: dict[str, TTSProvider] = {}
        self._default_provider = default_provider
        self._synthesis_count: int = 0

    def register_provider(self, provider: TTSProvider) -> None:
        """Register a TTS provider."""
        self._providers[provider.provider_name] = provider
        if not self._default_provider:
            self._default_provider = provider.provider_name
        logger.info("tts_provider_registered", provider=provider.provider_name)

    def list_providers(self) -> list[str]:
        """Return names of all registered providers."""
        return list(self._providers.keys())

    def list_voices(self, provider: str | None = None) -> list[str]:
        """List available voices for a provider."""
        name = provider or self._default_provider
        if name and name in self._providers:
            return self._providers[name].list_voices()
        return []

    async def synthesize(
        self,
        text: str,
        *,
        provider: str | None = None,
        voice: str = "alloy",
        model: str = "tts-1",
        format: AudioFormat = AudioFormat.MP3,
        speed: float = 1.0,
    ) -> TTSResult:
        """Convert text to speech audio.

        Parameters
        ----------
        text:
            Text to convert to speech.
        provider:
            Provider name. Falls back to default.
        voice:
            Voice to use.
        model:
            TTS model.
        format:
            Audio output format.
        speed:
            Playback speed multiplier.

        Returns
        -------
        TTSResult
            Generated audio data with metadata.
        """
        provider_name = provider or self._default_provider
        if not provider_name or provider_name not in self._providers:
            available = ", ".join(self._providers.keys()) or "none"
            raise ValueError(
                f"Unknown TTS provider '{provider_name}'. Available: {available}"
            )

        tts_provider = self._providers[provider_name]

        request = TTSRequest(
            text=text,
            voice=voice,
            model=model,
            format=format,
            speed=speed,
        )

        logger.info(
            "tts_started",
            provider=provider_name,
            voice=voice,
            text_length=len(text),
        )

        result = await tts_provider.synthesize(request)
        self._synthesis_count += 1

        logger.info(
            "tts_completed",
            provider=provider_name,
            format=result.format.value,
            total=self._synthesis_count,
        )

        return result

    @property
    def synthesis_count(self) -> int:
        """Total number of TTS syntheses performed."""
        return self._synthesis_count
