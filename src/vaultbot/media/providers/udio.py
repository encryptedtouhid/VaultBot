"""Udio music generation provider."""

from __future__ import annotations

import httpx

from vaultbot.media.music_generation import MusicGenerationRequest, MusicGenerationResult

_API_URL = "https://api.udio.com/v1"


class UdioProvider:
    """Udio music generation provider."""

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=_API_URL,
            timeout=120.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def provider_name(self) -> str:
        return "udio"

    async def generate(self, request: MusicGenerationRequest) -> MusicGenerationResult:
        resp = await self._client.post(
            "/generate",
            json={
                "prompt": request.prompt,
                "genre": request.genre.value,
                "duration": request.duration_seconds,
            },
        )
        resp.raise_for_status()
        return MusicGenerationResult(
            audio_data=resp.content,
            format=request.format,
            provider="udio",
            duration_seconds=request.duration_seconds,
        )

    async def close(self) -> None:
        await self._client.aclose()
