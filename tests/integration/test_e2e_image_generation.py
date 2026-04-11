"""E2E integration tests for image generation pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.media.base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageQuality,
    ImageSize,
)
from vaultbot.media.image_generation import ImageGenerationEngine
from vaultbot.media.providers.dalle import DalleProvider
from vaultbot.media.providers.stability import StabilityProvider


class TestE2EImageGeneration:
    @pytest.mark.asyncio
    async def test_dalle_full_pipeline(self) -> None:
        """Register DALL-E, generate, verify output."""
        engine = ImageGenerationEngine()

        dalle = DalleProvider(api_key="test_key")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {"url": "https://oai.example.com/sunset.png", "revised_prompt": "beautiful sunset"}
            ]
        }
        dalle._client = AsyncMock()
        dalle._client.post = AsyncMock(return_value=mock_resp)

        engine.register_provider(dalle)

        images = await engine.generate(
            "a sunset over mountains",
            size=ImageSize.LANDSCAPE_1792,
            quality=ImageQuality.HD,
        )

        assert len(images) == 1
        assert "oai.example.com" in images[0].url
        assert engine.generation_count == 1

    @pytest.mark.asyncio
    async def test_stability_full_pipeline(self) -> None:
        """Register Stability, generate, verify output."""
        engine = ImageGenerationEngine()

        stability = StabilityProvider(api_key="test_key")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "artifacts": [{"base64": "imgdata", "finishReason": "SUCCESS"}]
        }
        stability._client = AsyncMock()
        stability._client.post = AsyncMock(return_value=mock_resp)

        engine.register_provider(stability)

        images = await engine.generate("a robot cat")
        assert len(images) == 1
        assert images[0].b64_data == "imgdata"

    @pytest.mark.asyncio
    async def test_multi_provider_switching(self) -> None:
        """Register multiple providers and switch between them."""
        engine = ImageGenerationEngine()

        class FakeProvider:
            def __init__(self, name: str) -> None:
                self._name = name

            @property
            def provider_name(self) -> str:
                return self._name

            async def generate(self, request: ImageGenerationRequest) -> list[GeneratedImage]:
                return [
                    GeneratedImage(url=f"https://{self._name}.com/img.png", provider=self._name)
                ]

        engine.register_provider(FakeProvider("providerA"))
        engine.register_provider(FakeProvider("providerB"))

        img_a = await engine.generate("test", provider="providerA")
        assert img_a[0].provider == "providerA"

        img_b = await engine.generate("test", provider="providerB")
        assert img_b[0].provider == "providerB"

        assert engine.generation_count == 2

    @pytest.mark.asyncio
    async def test_default_provider_used_when_none_specified(self) -> None:
        """First registered provider is used as default."""
        engine = ImageGenerationEngine()

        class FakeProvider:
            def __init__(self, name: str) -> None:
                self._name = name

            @property
            def provider_name(self) -> str:
                return self._name

            async def generate(self, request: ImageGenerationRequest) -> list[GeneratedImage]:
                return [GeneratedImage(url="test", provider=self._name)]

        engine.register_provider(FakeProvider("first"))
        engine.register_provider(FakeProvider("second"))

        images = await engine.generate("test")
        assert images[0].provider == "first"
