"""Audio format normalization pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from vaultbot.media.stt import AudioFormat
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    """Metadata about an audio file."""

    format: AudioFormat
    size_bytes: int
    duration_seconds: float = 0.0
    sample_rate: int = 0
    channels: int = 0


@dataclass(frozen=True, slots=True)
class AudioPipelineConfig:
    """Configuration for audio pipeline."""

    max_size_bytes: int = 25 * 1024 * 1024  # 25 MB
    max_duration_seconds: float = 300.0  # 5 minutes
    target_format: AudioFormat = AudioFormat.WAV
    target_sample_rate: int = 16000


class AudioValidationError(Exception):
    """Raised when audio fails validation."""


_FORMAT_SIGNATURES: dict[bytes, AudioFormat] = {
    b"RIFF": AudioFormat.WAV,
    b"\xff\xfb": AudioFormat.MP3,
    b"\xff\xf3": AudioFormat.MP3,
    b"ID3": AudioFormat.MP3,
    b"fLaC": AudioFormat.FLAC,
    b"OggS": AudioFormat.OGG,
}


class AudioPipeline:
    """Audio format normalization and validation pipeline."""

    def __init__(self, config: AudioPipelineConfig | None = None) -> None:
        self._config = config or AudioPipelineConfig()

    @property
    def config(self) -> AudioPipelineConfig:
        return self._config

    def detect_format(self, audio_data: bytes) -> AudioFormat:
        """Detect audio format from file header bytes."""
        for sig, fmt in _FORMAT_SIGNATURES.items():
            if audio_data[: len(sig)] == sig:
                return fmt
        return AudioFormat.WAV  # default fallback

    def validate(self, audio_data: bytes) -> AudioMetadata:
        """Validate audio data against pipeline config."""
        if not audio_data:
            raise AudioValidationError("Empty audio data")

        size = len(audio_data)
        if size > self._config.max_size_bytes:
            raise AudioValidationError(
                f"Audio size {size} exceeds max {self._config.max_size_bytes} bytes"
            )

        fmt = self.detect_format(audio_data)
        metadata = AudioMetadata(format=fmt, size_bytes=size)

        logger.info(
            "audio_validated",
            format=fmt.value,
            size_bytes=size,
        )
        return metadata

    def normalize(self, audio_data: bytes) -> tuple[bytes, AudioMetadata]:
        """Validate and normalize audio data.

        Returns the (possibly converted) audio data and its metadata.
        Currently returns audio as-is after validation; format conversion
        requires ffmpeg or pydub which are optional dependencies.
        """
        metadata = self.validate(audio_data)
        return audio_data, metadata
