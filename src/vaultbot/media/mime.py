"""MIME type mapping and detection."""

from __future__ import annotations

_EXT_TO_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".txt": "text/plain",
    ".html": "text/html",
    ".md": "text/markdown",
}

_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "audio/wav"),
    (b"fLaC", "audio/flac"),
    (b"ID3", "audio/mpeg"),
    (b"%PDF", "application/pdf"),
]


def mime_from_extension(filename: str) -> str:
    """Detect MIME type from file extension."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXT_TO_MIME.get(ext, "application/octet-stream")


def mime_from_bytes(data: bytes) -> str:
    """Detect MIME type from file header bytes."""
    for sig, mime in _SIGNATURES:
        if data[: len(sig)] == sig:
            return mime
    return "application/octet-stream"


def is_image(mime: str) -> bool:
    return mime.startswith("image/")


def is_audio(mime: str) -> bool:
    return mime.startswith("audio/")


def is_video(mime: str) -> bool:
    return mime.startswith("video/")
