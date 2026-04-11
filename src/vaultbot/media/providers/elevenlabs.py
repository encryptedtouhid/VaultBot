"""ElevenLabs TTS provider."""

from __future__ import annotations

import httpx

from vaultbot.media.tts import AudioFormat, TTSRequest, TTSResult
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_BASE = "https://api.elevenlabs.io/v1"

_DEFAULT_VOICES = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "drew": "29vD33N1CtxCmqQRPOHJ",
    "clyde": "2EiwWnXFnvU5JabPnv8n",
    "paul": "5Q0t7uMcjvnagumLfvZi",
    "domi": "AZnzlk1XvdvUeBnXmlld",
    "dave": "CYw3kZ02Hs0563khs1Fj",
    "fin": "D38z5RcWu1voky8WS1ja",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
}


class ElevenLabsProvider:
    """ElevenLabs TTS provider.

    Parameters
    ----------
    api_key:
        ElevenLabs API key.
    default_voice_id:
        Default ElevenLabs voice ID.
    """

    def __init__(
        self,
        api_key: str,
        default_voice_id: str = "EXAVITQu4vr4xnSDxMaL",  # sarah
    ) -> None:
        self._api_key = api_key
        self._default_voice_id = default_voice_id
        self._client = httpx.AsyncClient(timeout=60.0)

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    def list_voices(self) -> list[str]:
        return list(_DEFAULT_VOICES.keys())

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        """Generate speech via ElevenLabs API."""
        voice_id = _DEFAULT_VOICES.get(request.voice, self._default_voice_id)

        url = f"{_API_BASE}/text-to-speech/{voice_id}"
        body = {
            "text": request.text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        resp = await self._client.post(
            url,
            json=body,
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
        )
        resp.raise_for_status()

        return TTSResult(
            audio_data=resp.content,
            format=AudioFormat.MP3,
            provider="elevenlabs",
            voice=request.voice,
        )

    async def close(self) -> None:
        await self._client.aclose()
