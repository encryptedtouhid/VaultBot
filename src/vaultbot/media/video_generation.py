"""Video generation engine with provider registry.

Supports text-to-video and image-to-video workflows through pluggable
providers.  Video generation is async (takes time), so the engine
supports status polling.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class VideoStatus(str, Enum):
    """Status of a video generation job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoAspectRatio(str, Enum):
    """Standard video aspect ratios."""

    SQUARE = "1:1"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    WIDE = "21:9"


@dataclass(frozen=True, slots=True)
class VideoGenerationRequest:
    """Parameters for a video generation request."""

    prompt: str
    aspect_ratio: VideoAspectRatio = VideoAspectRatio.LANDSCAPE
    duration_seconds: int = 5
    image_url: str = ""  # For image-to-video


@dataclass(frozen=True, slots=True)
class VideoGenerationResult:
    """Result from a video generation request."""

    job_id: str
    status: VideoStatus
    video_url: str = ""
    provider: str = ""
    duration_seconds: int = 0
    error: str = ""


@runtime_checkable
class VideoProvider(Protocol):
    """Protocol for video generation providers."""

    @property
    def provider_name(self) -> str: ...

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult: ...

    async def check_status(self, job_id: str) -> VideoGenerationResult: ...


class VideoGenerationEngine:
    """Orchestrates video generation across multiple providers."""

    def __init__(self, default_provider: str = "") -> None:
        self._providers: dict[str, VideoProvider] = {}
        self._default_provider = default_provider
        self._generation_count: int = 0

    def register_provider(self, provider: VideoProvider) -> None:
        self._providers[provider.provider_name] = provider
        if not self._default_provider:
            self._default_provider = provider.provider_name
        logger.info("video_provider_registered", provider=provider.provider_name)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    async def generate(
        self,
        prompt: str,
        *,
        provider: str | None = None,
        aspect_ratio: VideoAspectRatio = VideoAspectRatio.LANDSCAPE,
        duration_seconds: int = 5,
        image_url: str = "",
    ) -> VideoGenerationResult:
        provider_name = provider or self._default_provider
        if not provider_name or provider_name not in self._providers:
            available = ", ".join(self._providers.keys()) or "none"
            raise ValueError(f"Unknown video provider '{provider_name}'. Available: {available}")

        vid_provider = self._providers[provider_name]

        request = VideoGenerationRequest(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            image_url=image_url,
        )

        logger.info("video_generation_started", provider=provider_name, prompt=prompt[:100])
        result = await vid_provider.generate(request)
        self._generation_count += 1
        return result

    async def check_status(
        self, job_id: str, *, provider: str | None = None
    ) -> VideoGenerationResult:
        provider_name = provider or self._default_provider
        if not provider_name or provider_name not in self._providers:
            raise ValueError(f"Unknown video provider '{provider_name}'")
        return await self._providers[provider_name].check_status(job_id)

    @property
    def generation_count(self) -> int:
        return self._generation_count
