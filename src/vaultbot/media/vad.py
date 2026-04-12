"""Voice Activity Detection engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class VADState(str, Enum):
    """Voice activity state."""

    SILENCE = "silence"
    SPEECH = "speech"


@dataclass(frozen=True, slots=True)
class VADConfig:
    """VAD configuration."""

    sensitivity: float = 0.5
    silence_threshold_ms: int = 1500
    min_speech_ms: int = 250
    sample_rate: int = 16000
    frame_size_ms: int = 30


@dataclass(frozen=True, slots=True)
class VADSegment:
    """A detected speech segment."""

    start_ms: int
    end_ms: int
    confidence: float = 0.0


class VADEngine:
    """Voice Activity Detection engine.

    Uses energy-based detection with configurable sensitivity.
    Can be extended with webrtcvad or silero-vad backends.
    """

    def __init__(self, config: VADConfig | None = None) -> None:
        self._config = config or VADConfig()
        self._state = VADState.SILENCE
        self._speech_start_ms: int = 0
        self._silence_start_ms: int = 0

    @property
    def state(self) -> VADState:
        return self._state

    @property
    def config(self) -> VADConfig:
        return self._config

    def process_frame(self, frame: bytes, timestamp_ms: int) -> VADState:
        """Process an audio frame and return the current VAD state."""
        energy = self._compute_energy(frame)
        threshold = self._config.sensitivity

        if energy > threshold:
            if self._state == VADState.SILENCE:
                self._speech_start_ms = timestamp_ms
                self._state = VADState.SPEECH
                logger.debug("vad_speech_start", timestamp_ms=timestamp_ms)
            self._silence_start_ms = 0
        else:
            if self._state == VADState.SPEECH:
                if self._silence_start_ms == 0:
                    self._silence_start_ms = timestamp_ms
                elif (timestamp_ms - self._silence_start_ms) >= self._config.silence_threshold_ms:
                    self._state = VADState.SILENCE
                    logger.debug("vad_speech_end", timestamp_ms=timestamp_ms)

        return self._state

    def detect_segments(self, audio_data: bytes, sample_rate: int = 16000) -> list[VADSegment]:
        """Detect speech segments in audio data."""
        frame_bytes = (self._config.frame_size_ms * sample_rate * 2) // 1000
        segments: list[VADSegment] = []
        current_start: int | None = None

        for i in range(0, len(audio_data), frame_bytes):
            frame = audio_data[i : i + frame_bytes]
            if len(frame) < frame_bytes:
                break

            timestamp_ms = (i * 1000) // (sample_rate * 2)
            state = self.process_frame(frame, timestamp_ms)

            if state == VADState.SPEECH and current_start is None:
                current_start = timestamp_ms
            elif state == VADState.SILENCE and current_start is not None:
                duration = timestamp_ms - current_start
                if duration >= self._config.min_speech_ms:
                    segments.append(VADSegment(start_ms=current_start, end_ms=timestamp_ms))
                current_start = None

        if current_start is not None:
            end_ms = (len(audio_data) * 1000) // (sample_rate * 2)
            segments.append(VADSegment(start_ms=current_start, end_ms=end_ms))

        self.reset()
        return segments

    def reset(self) -> None:
        """Reset VAD state."""
        self._state = VADState.SILENCE
        self._speech_start_ms = 0
        self._silence_start_ms = 0

    @staticmethod
    def _compute_energy(frame: bytes) -> float:
        """Compute normalized energy of an audio frame."""
        if not frame:
            return 0.0
        samples = [
            int.from_bytes(frame[i : i + 2], byteorder="little", signed=True)
            for i in range(0, len(frame) - 1, 2)
        ]
        if not samples:
            return 0.0
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        return min(rms / 32768.0, 1.0)
