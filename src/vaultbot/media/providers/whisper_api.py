"""OpenAI Whisper API STT provider."""

from __future__ import annotations

import httpx

from vaultbot.media.stt import AudioFormat, STTRequest, STTResult
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.openai.com/v1/audio/transcriptions"

_SUPPORTED_FORMATS = [
    AudioFormat.MP3, AudioFormat.WAV, AudioFormat.OGG,
    AudioFormat.FLAC, AudioFormat.WEBM, AudioFormat.M4A,
]


class WhisperAPIProvider:
    """OpenAI Whisper API provider for speech-to-text."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=120.0)

    @property
    def provider_name(self) -> str:
        return "whisper_api"

    def supported_formats(self) -> list[AudioFormat]:
        return list(_SUPPORTED_FORMATS)

    async def transcribe(self, request: STTRequest) -> STTResult:
        files = {"file": (f"audio.{request.format.value}", request.audio_data)}
        data: dict[str, str] = {"model": request.model}
        if request.language and request.language != "auto":
            data["language"] = request.language
        if request.prompt:
            data["prompt"] = request.prompt
        data["response_format"] = "verbose_json"

        resp = await self._client.post(
            _API_URL,
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        resp.raise_for_status()
        body = resp.json()

        return STTResult(
            text=body.get("text", ""),
            language=body.get("language", ""),
            provider="whisper_api",
            duration_seconds=body.get("duration", 0.0),
            confidence=1.0,
            segments=body.get("segments", []),
        )

    async def close(self) -> None:
        await self._client.aclose()
