"""Music generation engine with provider registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class MusicGenre(str, Enum):
    POP = "pop"
    ROCK = "rock"
    JAZZ = "jazz"
    CLASSICAL = "classical"
    ELECTRONIC = "electronic"
    AMBIENT = "ambient"


@dataclass(frozen=True, slots=True)
class MusicGenerationRequest:
    prompt: str
    genre: MusicGenre = MusicGenre.POP
    duration_seconds: int = 30
    format: str = "mp3"


@dataclass(frozen=True, slots=True)
class MusicGenerationResult:
    audio_data: bytes
    format: str
    provider: str
    duration_seconds: int = 0


@runtime_checkable
class MusicProvider(Protocol):
    @property
    def provider_name(self) -> str: ...
    async def generate(self, request: MusicGenerationRequest) -> MusicGenerationResult: ...


class MusicGenerationEngine:
    def __init__(self, default_provider: str = "") -> None:
        self._providers: dict[str, MusicProvider] = {}
        self._default_provider = default_provider
        self._count: int = 0

    def register_provider(self, provider: MusicProvider) -> None:
        self._providers[provider.provider_name] = provider
        if not self._default_provider:
            self._default_provider = provider.provider_name

    async def generate(
        self, prompt: str, *, provider: str | None = None, **kwargs: object
    ) -> MusicGenerationResult:
        name = provider or self._default_provider
        if not name or name not in self._providers:
            raise ValueError(f"Unknown music provider '{name}'")
        req = MusicGenerationRequest(
            prompt=prompt,
            **{k: v for k, v in kwargs.items() if k in MusicGenerationRequest.__dataclass_fields__},
        )
        result = await self._providers[name].generate(req)
        self._count += 1
        return result

    @property
    def generation_count(self) -> int:
        return self._count
