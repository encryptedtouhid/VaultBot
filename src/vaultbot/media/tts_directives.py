"""SSML-like text processing directives for TTS."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SUPPORTED_LANGUAGES = frozenset(
    {
        "en",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "ja",
        "ko",
        "zh",
        "ar",
        "hi",
        "ru",
    }
)

_MAX_TEXT_LENGTH = 5000


@dataclass(frozen=True, slots=True)
class TTSDirective:
    voice: str = ""
    speed: float = 1.0
    pitch: str = "medium"
    language: str = "en"
    emphasis: str = ""


def parse_directives(text: str) -> tuple[TTSDirective, str]:
    """Extract TTS directives from text prefix and return (directive, clean_text)."""
    directive = TTSDirective()
    clean = text

    voice_match = re.match(r"^voice:(\S+)\s*\n?", text)
    if voice_match:
        directive = TTSDirective(voice=voice_match.group(1))
        clean = text[voice_match.end() :]

    speed_match = re.search(r"speed:(\d+\.?\d*)", text)
    if speed_match:
        directive = TTSDirective(
            voice=directive.voice,
            speed=float(speed_match.group(1)),
            language=directive.language,
        )
        clean = re.sub(r"speed:\d+\.?\d*\s*", "", clean)

    return directive, clean.strip()


def validate_language(lang: str) -> bool:
    """Check if a language code is supported."""
    return lang.lower()[:2] in _SUPPORTED_LANGUAGES


def truncate_for_tts(text: str, max_length: int = _MAX_TEXT_LENGTH) -> str:
    """Truncate text to TTS max length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
