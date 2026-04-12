"""Realtime bidirectional voice streaming with provider registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class VoiceSessionState(str, Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass(slots=True)
class VoiceSessionConfig:
    sample_rate: int = 24000
    audio_format: str = "pcm16"
    language: str = "en"
    model: str = ""
    tools: list[dict[str, object]] = field(default_factory=list)


@dataclass(slots=True)
class VoiceSession:
    session_id: str = ""
    state: VoiceSessionState = VoiceSessionState.IDLE
    config: VoiceSessionConfig = field(default_factory=VoiceSessionConfig)
    transcript_user: str = ""
    transcript_assistant: str = ""


TranscriptCallback = Callable[[str, str], None]  # (role, text)


@runtime_checkable
class RealtimeVoiceProvider(Protocol):
    @property
    def provider_name(self) -> str: ...
    async def connect(self, config: VoiceSessionConfig) -> VoiceSession: ...
    async def send_audio(self, session_id: str, audio_data: bytes) -> None: ...
    async def receive_audio(self, session_id: str) -> bytes: ...
    async def disconnect(self, session_id: str) -> None: ...


class RealtimeVoiceRegistry:
    """Registry for realtime voice providers."""

    def __init__(self) -> None:
        self._providers: dict[str, RealtimeVoiceProvider] = {}
        self._default: str = ""

    def register(self, provider: RealtimeVoiceProvider) -> None:
        self._providers[provider.provider_name] = provider
        if not self._default:
            self._default = provider.provider_name

    def get(self, name: str = "") -> RealtimeVoiceProvider | None:
        return self._providers.get(name or self._default)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())
