"""Language detection for incoming messages."""

from __future__ import annotations

import re

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Unicode ranges for common scripts
_SCRIPT_PATTERNS: dict[str, str] = {
    "zh": r"[\u4e00-\u9fff]",
    "ja": r"[\u3040-\u30ff]",
    "ko": r"[\uac00-\ud7af]",
    "ar": r"[\u0600-\u06ff]",
    "hi": r"[\u0900-\u097f]",
    "th": r"[\u0e00-\u0e7f]",
    "ru": r"[\u0400-\u04ff]",
}


def detect_language(text: str) -> str:
    """Detect the language of a text using script heuristics.

    Returns a language code or 'en' as default.
    """
    if not text.strip():
        return "en"

    for lang, pattern in _SCRIPT_PATTERNS.items():
        if re.search(pattern, text):
            return lang

    return "en"


def is_rtl(locale: str) -> bool:
    """Check if a locale uses right-to-left text."""
    return locale in {"ar", "he", "fa", "ur"}
