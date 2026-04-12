"""Secret redaction in log output."""

from __future__ import annotations

import re

_SECRET_PATTERNS = [
    (re.compile(r"(sk-[a-zA-Z0-9]{20,})"), r"sk-****"),
    (re.compile(r"(token[\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9_\-]{20,})"), r"\1****"),
    (re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)([^\s\"',]+)"), r"\1****"),
    (re.compile(r"(Bearer\s+)([a-zA-Z0-9_\-\.]+)"), r"\1****"),
]


def redact_secrets(text: str) -> str:
    """Redact common secret patterns from text."""
    result = text
    for pattern, replacement in _SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact_dict(
    data: dict[str, object], sensitive_keys: set[str] | None = None
) -> dict[str, object]:
    """Redact sensitive keys in a dictionary."""
    keys = sensitive_keys or {"password", "secret", "token", "api_key", "credential"}
    result: dict[str, object] = {}
    for k, v in data.items():
        if any(sk in k.lower() for sk in keys):
            result[k] = "****"
        elif isinstance(v, dict):
            result[k] = redact_dict(v, keys)  # type: ignore[arg-type]
        else:
            result[k] = v
    return result
