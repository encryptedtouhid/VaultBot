"""Stability AI (Stable Diffusion) image generation provider."""

from __future__ import annotations

import httpx

from vaultbot.media.base import GeneratedImage, ImageGenerationRequest
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.stability.ai/v1/generation"

# Map our sizes to Stability dimensions
_SIZE_MAP = {
    "256x256": (256, 256),
    "512x512": (512, 512),
    "1024x1024": (1024, 1024),
    "1792x1024": (1792, 1024),
    "1024x1792": (1024, 1792),
}


class StabilityProvider:
    """Stability AI image generation provider.

    Parameters
    ----------
    api_key:
        Stability AI API key.
    engine_id:
        Engine to use (e.g. ``stable-diffusion-xl-1024-v1-0``).
    """

    def __init__(self, api_key: str, engine_id: str = "stable-diffusion-xl-1024-v1-0") -> None:
        self._api_key = api_key
        self._engine_id = engine_id
        self._client = httpx.AsyncClient(timeout=120.0)

    @property
    def provider_name(self) -> str:
        return "stability"

    async def generate(self, request: ImageGenerationRequest) -> list[GeneratedImage]:
        """Generate images via the Stability AI API."""
        width, height = _SIZE_MAP.get(request.size.value, (1024, 1024))

        body = {
            "text_prompts": [{"text": request.prompt, "weight": 1.0}],
            "cfg_scale": 7,
            "width": width,
            "height": height,
            "samples": request.n,
            "steps": 30,
        }

        url = f"{_API_URL}/{self._engine_id}/text-to-image"
        resp = await self._client.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        images: list[GeneratedImage] = []
        for artifact in data.get("artifacts", []):
            images.append(
                GeneratedImage(
                    url="",
                    b64_data=artifact.get("base64", ""),
                    provider="stability",
                    model=self._engine_id,
                    size=request.size.value,
                )
            )

        return images

    async def close(self) -> None:
        await self._client.aclose()
