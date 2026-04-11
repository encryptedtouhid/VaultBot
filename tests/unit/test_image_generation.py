"""Unit tests for image generation engine and providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.media.base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageProvider,
    ImageQuality,
    ImageSize,
    ImageStyle,
)
from vaultbot.media.image_generation import ImageGenerationEngine


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockImageProvider:
    def __init__(self, name: str = "mock_img") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(self, request: ImageGenerationRequest) -> list[GeneratedImage]:
        return [
            GeneratedImage(
                url=f"https://example.com/{self._name}.png",
                revised_prompt=f"revised: {request.prompt}",
                provider=self._name,
                model="mock-model",
                size=request.size.value,
            )
        ]


# ---------------------------------------------------------------------------
# Base types
# ---------------------------------------------------------------------------


class TestBaseTypes:
    def test_image_size_enum(self) -> None:
        assert ImageSize.SQUARE_1024.value == "1024x1024"
        assert ImageSize.LANDSCAPE_1792.value == "1792x1024"

    def test_image_quality_enum(self) -> None:
        assert ImageQuality.HD.value == "hd"

    def test_image_style_enum(self) -> None:
        assert ImageStyle.VIVID.value == "vivid"

    def test_generated_image_dataclass(self) -> None:
        img = GeneratedImage(url="https://example.com/img.png", provider="test")
        assert img.url == "https://example.com/img.png"
        assert img.revised_prompt == ""

    def test_request_defaults(self) -> None:
        req = ImageGenerationRequest(prompt="a cat")
        assert req.size == ImageSize.SQUARE_1024
        assert req.quality == ImageQuality.STANDARD
        assert req.n == 1

    def test_mock_is_image_provider(self) -> None:
        assert isinstance(MockImageProvider(), ImageProvider)


# ---------------------------------------------------------------------------
# Image Generation Engine
# ---------------------------------------------------------------------------


class TestImageGenerationEngine:
    def test_register_provider(self) -> None:
        engine = ImageGenerationEngine()
        engine.register_provider(MockImageProvider("dalle"))
        assert "dalle" in engine.list_providers()

    def test_first_registered_becomes_default(self) -> None:
        engine = ImageGenerationEngine()
        engine.register_provider(MockImageProvider("dalle"))
        engine.register_provider(MockImageProvider("stability"))
        assert engine._default_provider == "dalle"

    def test_explicit_default(self) -> None:
        engine = ImageGenerationEngine(default_provider="stability")
        engine.register_provider(MockImageProvider("dalle"))
        engine.register_provider(MockImageProvider("stability"))
        assert engine._default_provider == "stability"

    def test_list_providers(self) -> None:
        engine = ImageGenerationEngine()
        engine.register_provider(MockImageProvider("a"))
        engine.register_provider(MockImageProvider("b"))
        assert engine.list_providers() == ["a", "b"]

    @pytest.mark.asyncio
    async def test_generate_success(self) -> None:
        engine = ImageGenerationEngine()
        engine.register_provider(MockImageProvider("dalle"))

        images = await engine.generate("a sunset over mountains")
        assert len(images) == 1
        assert "example.com" in images[0].url
        assert images[0].provider == "dalle"
        assert engine.generation_count == 1

    @pytest.mark.asyncio
    async def test_generate_with_specific_provider(self) -> None:
        engine = ImageGenerationEngine()
        engine.register_provider(MockImageProvider("dalle"))
        engine.register_provider(MockImageProvider("stability"))

        images = await engine.generate("a cat", provider="stability")
        assert images[0].provider == "stability"

    @pytest.mark.asyncio
    async def test_generate_unknown_provider_raises(self) -> None:
        engine = ImageGenerationEngine()
        engine.register_provider(MockImageProvider("dalle"))

        with pytest.raises(ValueError, match="Unknown image provider"):
            await engine.generate("test", provider="nonexistent")

    @pytest.mark.asyncio
    async def test_generate_no_providers_raises(self) -> None:
        engine = ImageGenerationEngine()

        with pytest.raises(ValueError, match="Unknown image provider"):
            await engine.generate("test")

    @pytest.mark.asyncio
    async def test_generate_with_options(self) -> None:
        engine = ImageGenerationEngine()
        engine.register_provider(MockImageProvider("dalle"))

        images = await engine.generate(
            "a dog",
            size=ImageSize.LANDSCAPE_1792,
            quality=ImageQuality.HD,
            style=ImageStyle.NATURAL,
        )
        assert images[0].size == "1792x1024"

    @pytest.mark.asyncio
    async def test_generation_count_increments(self) -> None:
        engine = ImageGenerationEngine()
        engine.register_provider(MockImageProvider("dalle"))

        await engine.generate("img1")
        await engine.generate("img2")
        assert engine.generation_count == 2


# ---------------------------------------------------------------------------
# DALL-E Provider
# ---------------------------------------------------------------------------


class TestDalleProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.dalle import DalleProvider
        provider = DalleProvider(api_key="test")
        assert provider.provider_name == "dalle"

    def test_default_model(self) -> None:
        from vaultbot.media.providers.dalle import DalleProvider
        provider = DalleProvider(api_key="test")
        assert provider._model == "dall-e-3"

    @pytest.mark.asyncio
    async def test_generate_calls_api(self) -> None:
        from vaultbot.media.providers.dalle import DalleProvider
        provider = DalleProvider(api_key="test")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": [{
                "url": "https://oai.example.com/img.png",
                "revised_prompt": "a beautiful sunset",
            }]
        }
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        req = ImageGenerationRequest(prompt="a sunset")
        images = await provider.generate(req)

        assert len(images) == 1
        assert images[0].url == "https://oai.example.com/img.png"
        assert images[0].revised_prompt == "a beautiful sunset"
        assert images[0].provider == "dalle"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        from vaultbot.media.providers.dalle import DalleProvider
        provider = DalleProvider(api_key="test")
        provider._client = AsyncMock()
        await provider.close()
        provider._client.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# Stability Provider
# ---------------------------------------------------------------------------


class TestStabilityProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.stability import StabilityProvider
        provider = StabilityProvider(api_key="test")
        assert provider.provider_name == "stability"

    @pytest.mark.asyncio
    async def test_generate_calls_api(self) -> None:
        from vaultbot.media.providers.stability import StabilityProvider
        provider = StabilityProvider(api_key="test")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "artifacts": [{"base64": "abc123base64data", "finishReason": "SUCCESS"}]
        }
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_resp)

        req = ImageGenerationRequest(prompt="a cat")
        images = await provider.generate(req)

        assert len(images) == 1
        assert images[0].b64_data == "abc123base64data"
        assert images[0].provider == "stability"
