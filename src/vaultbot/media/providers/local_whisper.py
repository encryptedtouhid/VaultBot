"""Local Whisper STT provider using faster-whisper or whisper."""

from __future__ import annotations

from vaultbot.media.stt import AudioFormat, STTRequest, STTResult
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_SUPPORTED_FORMATS = [AudioFormat.WAV, AudioFormat.MP3, AudioFormat.FLAC, AudioFormat.OGG]


class LocalWhisperProvider:
    """Local Whisper provider for on-device transcription.

    Uses faster-whisper if available, falls back to a stub for environments
    where the library is not installed.
    """

    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size
        self._model: object | None = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-untyped]

            self._model = WhisperModel(self._model_size, compute_type="int8")
            logger.info("local_whisper_loaded", model=self._model_size)
        except ImportError:
            logger.warning(
                "local_whisper_unavailable",
                reason="faster-whisper not installed",
            )
            self._model = None

    @property
    def provider_name(self) -> str:
        return "local_whisper"

    def supported_formats(self) -> list[AudioFormat]:
        return list(_SUPPORTED_FORMATS)

    async def transcribe(self, request: STTRequest) -> STTResult:
        if self._model is None:
            raise RuntimeError(
                "Local Whisper model not available. Install faster-whisper."
            )

        import tempfile
        from pathlib import Path

        suffix = f".{request.format.value}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(request.audio_data)
            tmp_path = Path(tmp.name)

        try:
            segments_iter, info = self._model.transcribe(  # type: ignore[union-attr]
                str(tmp_path),
                language=request.language if request.language != "auto" else None,
            )
            segments = list(segments_iter)
            text = " ".join(s.text.strip() for s in segments)

            return STTResult(
                text=text,
                language=info.language,
                provider="local_whisper",
                duration_seconds=info.duration,
                confidence=sum(s.avg_logprob for s in segments) / max(len(segments), 1),
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    async def close(self) -> None:
        self._model = None
