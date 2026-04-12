"""Kling AI video generation provider."""

from __future__ import annotations

import httpx

from vaultbot.media.video_generation import (
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoStatus,
)

_API_URL = "https://api.klingai.com/v1"


class KlingProvider:
    """Kling AI video generation provider."""

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=_API_URL,
            timeout=120.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def provider_name(self) -> str:
        return "kling"

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        resp = await self._client.post(
            "/video/generate",
            json={
                "prompt": request.prompt,
                "aspect_ratio": request.aspect_ratio.value,
                "duration": request.duration_seconds,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return VideoGenerationResult(
            job_id=data.get("task_id", ""),
            status=VideoStatus.PENDING,
            provider="kling",
        )

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        resp = await self._client.get(f"/video/status/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        status_map = {"completed": VideoStatus.COMPLETED, "failed": VideoStatus.FAILED}
        return VideoGenerationResult(
            job_id=job_id,
            status=status_map.get(data.get("status", ""), VideoStatus.PROCESSING),
            video_url=data.get("video_url", ""),
            provider="kling",
        )

    async def close(self) -> None:
        await self._client.aclose()
