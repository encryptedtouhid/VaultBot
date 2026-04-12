"""Deepgram STT provider."""

from __future__ import annotations

import httpx

from vaultbot.media.stt import AudioFormat, STTRequest, STTResult
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.deepgram.com/v1/listen"

_MIME_MAP: dict[AudioFormat, str] = {
    AudioFormat.WAV: "audio/wav",
    AudioFormat.MP3: "audio/mpeg",
    AudioFormat.OGG: "audio/ogg",
    AudioFormat.FLAC: "audio/flac",
    AudioFormat.WEBM: "audio/webm",
    AudioFormat.M4A: "audio/mp4",
    AudioFormat.AAC: "audio/aac",
    AudioFormat.OPUS: "audio/opus",
}

_SUPPORTED_FORMATS = list(_MIME_MAP.keys())


class DeepgramProvider:
    """Deepgram real-time and batch STT provider."""

    def __init__(self, api_key: str, model: str = "nova-2") -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    @property
    def provider_name(self) -> str:
        return "deepgram"

    def supported_formats(self) -> list[AudioFormat]:
        return list(_SUPPORTED_FORMATS)

    async def transcribe(self, request: STTRequest) -> STTResult:
        params: dict[str, str] = {
            "model": self._model,
            "punctuate": "true",
            "utterances": "true",
        }
        if request.language and request.language != "auto":
            params["language"] = request.language
        else:
            params["detect_language"] = "true"

        mime = _MIME_MAP.get(request.format, "audio/wav")

        resp = await self._client.post(
            _API_URL,
            params=params,
            content=request.audio_data,
            headers={
                "Authorization": f"Token {self._api_key}",
                "Content-Type": mime,
            },
        )
        resp.raise_for_status()
        body = resp.json()

        results = body.get("results", {})
        channels = results.get("channels", [{}])
        alt = channels[0].get("alternatives", [{}])[0] if channels else {}

        return STTResult(
            text=alt.get("transcript", ""),
            language=results.get("channels", [{}])[0].get("detected_language", "")
            if channels
            else "",
            provider="deepgram",
            duration_seconds=body.get("metadata", {}).get("duration", 0.0),
            confidence=alt.get("confidence", 0.0),
        )

    async def close(self) -> None:
        await self._client.aclose()
