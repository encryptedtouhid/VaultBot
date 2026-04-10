"""Input sanitization for messages before processing.

Strips potentially dangerous content, normalizes input, and enforces
size limits to prevent abuse.
"""

from __future__ import annotations

import re
import unicodedata

from zenbot.utils.logging import get_logger

logger = get_logger(__name__)

# Maximum message length (characters)
MAX_MESSAGE_LENGTH = 4096

# Patterns to strip from input
_STRIP_PATTERNS: list[re.Pattern[str]] = [
    # Zero-width characters used for invisible text injection
    re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff]"),
    # Control characters (except newlines and tabs)
    re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"),
    # Directional override characters (used to reverse text display)
    re.compile(r"[\u202a-\u202e\u2066-\u2069]"),
]


def sanitize(text: str, *, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """Sanitize user input text.

    - Strips zero-width and control characters
    - Normalizes Unicode to NFC form
    - Truncates to max length
    - Strips leading/trailing whitespace
    """
    # Normalize Unicode
    text = unicodedata.normalize("NFC", text)

    # Strip dangerous patterns
    for pattern in _STRIP_PATTERNS:
        text = pattern.sub("", text)

    # Strip whitespace
    text = text.strip()

    # Enforce length limit
    if len(text) > max_length:
        logger.warning(
            "message_truncated",
            original_length=len(text),
            max_length=max_length,
        )
        text = text[:max_length]

    return text


def is_empty_after_sanitization(text: str) -> bool:
    """Check if text would be empty after sanitization."""
    return len(sanitize(text)) == 0


def contains_excessive_repetition(text: str, *, threshold: int = 50) -> bool:
    """Detect if text contains excessive character or word repetition.

    This can indicate a denial-of-service attempt or token waste attack.
    """
    # Check for single character repeated
    for match in re.finditer(r"(.)\1{" + str(threshold) + r",}", text):
        logger.warning(
            "excessive_repetition",
            char=match.group(1),
            count=len(match.group(0)),
        )
        return True

    # Check for word/phrase repeated
    for match in re.finditer(
        r"(\b\w+\b)(?:\s+\1){" + str(threshold // 5) + r",}",
        text,
        re.IGNORECASE,
    ):
        logger.warning("excessive_word_repetition", word=match.group(1))
        return True

    return False
