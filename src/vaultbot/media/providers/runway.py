"""Runway ML video generation provider."""

from __future__ import annotations

import httpx

from vaultbot.media.video_generation import (
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoStatus,
)
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.runwayml.com/v1"


class RunwayProvider:
    """Runway ML video generation provider."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=_API_URL,
            timeout=120.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def provider_name(self) -> str:
        return "runway"

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        resp = await self._client.post(
            "/generations",
            json={
                "prompt": request.prompt,
                "aspect_ratio": request.aspect_ratio.value,
                "duration": request.duration_seconds,
                "image_url": request.image_url or None,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return VideoGenerationResult(
            job_id=data.get("id", ""),
            status=VideoStatus.PENDING,
            provider="runway",
        )

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        resp = await self._client.get(f"/generations/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        status_map = {"completed": VideoStatus.COMPLETED, "failed": VideoStatus.FAILED}
        return VideoGenerationResult(
            job_id=job_id,
            status=status_map.get(data.get("status", ""), VideoStatus.PROCESSING),
            video_url=data.get("output_url", ""),
            provider="runway",
        )

    async def close(self) -> None:
        await self._client.aclose()
