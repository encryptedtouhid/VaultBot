"""OpenAI TTS provider."""

from __future__ import annotations

import httpx

from vaultbot.media.tts import TTSRequest, TTSResult
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.openai.com/v1/audio/speech"

_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class OpenAITTSProvider:
    """OpenAI TTS provider using the /v1/audio/speech endpoint.

    Parameters
    ----------
    api_key:
        OpenAI API key.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=60.0)

    @property
    def provider_name(self) -> str:
        return "openai_tts"

    def list_voices(self) -> list[str]:
        return list(_VOICES)

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        """Generate speech audio via OpenAI TTS API."""
        body = {
            "model": request.model,
            "input": request.text,
            "voice": request.voice,
            "response_format": request.format.value,
            "speed": request.speed,
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

        return TTSResult(
            audio_data=resp.content,
            format=request.format,
            provider="openai_tts",
            voice=request.voice,
        )

    async def close(self) -> None:
        await self._client.aclose()
