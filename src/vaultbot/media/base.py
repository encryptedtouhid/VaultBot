"""Base types for media generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


class ImageSize(str, Enum):
    """Standard image sizes."""
    SQUARE_256 = "256x256"
    SQUARE_512 = "512x512"
    SQUARE_1024 = "1024x1024"
    LANDSCAPE_1792 = "1792x1024"
    PORTRAIT_1024 = "1024x1792"


class ImageQuality(str, Enum):
    """Image quality levels."""
    STANDARD = "standard"
    HD = "hd"


class ImageStyle(str, Enum):
    """Image style options."""
    VIVID = "vivid"
    NATURAL = "natural"


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    """Result from an image generation request."""
    url: str
    revised_prompt: str = ""
    provider: str = ""
    model: str = ""
    size: str = ""
    b64_data: str = ""


@dataclass(frozen=True, slots=True)
class ImageGenerationRequest:
    """Parameters for an image generation request."""
    prompt: str
    size: ImageSize = ImageSize.SQUARE_1024
    quality: ImageQuality = ImageQuality.STANDARD
    style: ImageStyle = ImageStyle.VIVID
    n: int = 1


@runtime_checkable
class ImageProvider(Protocol):
    """Protocol for image generation providers."""

    @property
    def provider_name(self) -> str: ...

    async def generate(self, request: ImageGenerationRequest) -> list[GeneratedImage]: ...
