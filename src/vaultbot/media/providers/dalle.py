"""DALL-E image generation provider via OpenAI API."""

from __future__ import annotations

import httpx

from vaultbot.media.base import GeneratedImage, ImageGenerationRequest
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.openai.com/v1/images/generations"


class DalleProvider:
    """OpenAI DALL-E image generation provider.

    Parameters
    ----------
    api_key:
        OpenAI API key.
    model:
        DALL-E model version (``dall-e-2`` or ``dall-e-3``).
    """

    def __init__(self, api_key: str, model: str = "dall-e-3") -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    @property
    def provider_name(self) -> str:
        return "dalle"

    async def generate(self, request: ImageGenerationRequest) -> list[GeneratedImage]:
        """Generate images via the OpenAI images API."""
        body: dict = {
            "model": self._model,
            "prompt": request.prompt,
            "n": request.n,
            "size": request.size.value,
            "quality": request.quality.value,
            "style": request.style.value,
            "response_format": "url",
        }

        resp = await self._client.post(
            _API_URL,
            json=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        images: list[GeneratedImage] = []
        for item in data.get("data", []):
            images.append(
                GeneratedImage(
                    url=item.get("url", ""),
                    revised_prompt=item.get("revised_prompt", ""),
                    provider="dalle",
                    model=self._model,
                    size=request.size.value,
                )
            )

        return images

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
