"""Streaming transcription with partial/final callbacks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class TranscriptType(str, Enum):
    PARTIAL = "partial"
    FINAL = "final"


@dataclass(frozen=True, slots=True)
class TranscriptEvent:
    text: str
    transcript_type: TranscriptType
    confidence: float = 0.0
    language: str = ""
    is_speech_start: bool = False


TranscriptCallback = Callable[[TranscriptEvent], None]


@runtime_checkable
class RealtimeTranscriptionProvider(Protocol):
    @property
    def provider_name(self) -> str: ...
    async def start(self, language: str, callback: TranscriptCallback) -> str: ...
    async def send_audio(self, session_id: str, audio_data: bytes) -> None: ...
    async def stop(self, session_id: str) -> None: ...


class RealtimeTranscriptionRegistry:
    """Registry for streaming transcription providers."""

    def __init__(self) -> None:
        self._providers: dict[str, RealtimeTranscriptionProvider] = {}
        self._default: str = ""

    def register(self, provider: RealtimeTranscriptionProvider) -> None:
        self._providers[provider.provider_name] = provider
        if not self._default:
            self._default = provider.provider_name

    def get(self, name: str = "") -> RealtimeTranscriptionProvider | None:
        return self._providers.get(name or self._default)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())
