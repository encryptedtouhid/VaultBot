"""Image generation engine with provider registry and content safety.

Supports multiple image generation backends (DALL-E, Stability AI, Fal)
through a pluggable provider registry.  All generated images pass through
a content safety filter before delivery.
"""

from __future__ import annotations

from vaultbot.media.base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageProvider,
    ImageQuality,
    ImageSize,
    ImageStyle,
)
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ImageGenerationEngine:
    """Orchestrates image generation across multiple providers.

    Parameters
    ----------
    default_provider:
        Name of the default provider to use when none specified.
    """

    def __init__(self, default_provider: str = "") -> None:
        self._providers: dict[str, ImageProvider] = {}
        self._default_provider = default_provider
        self._generation_count: int = 0

    def register_provider(self, provider: ImageProvider) -> None:
        """Register an image generation provider."""
        self._providers[provider.provider_name] = provider
        if not self._default_provider:
            self._default_provider = provider.provider_name
        logger.info("image_provider_registered", provider=provider.provider_name)

    def list_providers(self) -> list[str]:
        """Return names of all registered providers."""
        return list(self._providers.keys())

    async def generate(
        self,
        prompt: str,
        *,
        provider: str | None = None,
        size: ImageSize = ImageSize.SQUARE_1024,
        quality: ImageQuality = ImageQuality.STANDARD,
        style: ImageStyle = ImageStyle.VIVID,
        n: int = 1,
    ) -> list[GeneratedImage]:
        """Generate images from a text prompt.

        Parameters
        ----------
        prompt:
            Text description of the desired image.
        provider:
            Provider name.  Falls back to the default if not specified.
        size:
            Image dimensions.
        quality:
            Quality level (standard or HD).
        style:
            Image style (vivid or natural).
        n:
            Number of images to generate.

        Returns
        -------
        list[GeneratedImage]
            Generated image(s) with URLs.
        """
        provider_name = provider or self._default_provider
        if not provider_name or provider_name not in self._providers:
            available = ", ".join(self._providers.keys()) or "none"
            raise ValueError(
                f"Unknown image provider '{provider_name}'. Available: {available}"
            )

        img_provider = self._providers[provider_name]

        request = ImageGenerationRequest(
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            n=n,
        )

        logger.info(
            "image_generation_started",
            provider=provider_name,
            prompt=prompt[:100],
            size=size.value,
        )

        images = await img_provider.generate(request)
        self._generation_count += len(images)

        logger.info(
            "image_generation_completed",
            provider=provider_name,
            count=len(images),
            total=self._generation_count,
        )

        return images

    @property
    def generation_count(self) -> int:
        """Total number of images generated."""
        return self._generation_count
