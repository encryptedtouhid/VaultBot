"""Extract model/thinking/verbose directives from message text."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class MessageDirectives:
    """Directives extracted from a message."""

    model: str = ""
    thinking: bool = False
    verbose: bool = False
    reasoning: bool = False
    abort: bool = False
    queue: bool = False
    clean_text: str = ""


_DIRECTIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "model": re.compile(r"^/model\s+(\S+)", re.MULTILINE),
    "thinking": re.compile(r"\bthink(?:ing)?:\s*(?:on|true|yes)\b", re.IGNORECASE),
    "verbose": re.compile(r"\bverbose:\s*(?:on|true|yes)\b", re.IGNORECASE),
    "reasoning": re.compile(r"\breason(?:ing)?:\s*(?:on|true|yes)\b", re.IGNORECASE),
    "abort": re.compile(r"^/abort\b", re.MULTILINE),
    "queue": re.compile(r"^/queue\b", re.MULTILINE),
}


def extract_directives(text: str) -> MessageDirectives:
    """Extract all directives from message text and return cleaned text."""
    directives = MessageDirectives()
    clean = text

    model_match = _DIRECTIVE_PATTERNS["model"].search(text)
    if model_match:
        directives.model = model_match.group(1)
        clean = clean[: model_match.start()] + clean[model_match.end() :]

    directives.thinking = bool(_DIRECTIVE_PATTERNS["thinking"].search(text))
    directives.verbose = bool(_DIRECTIVE_PATTERNS["verbose"].search(text))
    directives.reasoning = bool(_DIRECTIVE_PATTERNS["reasoning"].search(text))
    directives.abort = bool(_DIRECTIVE_PATTERNS["abort"].search(text))
    directives.queue = bool(_DIRECTIVE_PATTERNS["queue"].search(text))

    # Remove all directive patterns from clean text
    for pattern in _DIRECTIVE_PATTERNS.values():
        clean = pattern.sub("", clean)

    directives.clean_text = clean.strip()
    return directives
