"""Environment variable substitution in config values."""

from __future__ import annotations

import os
import re

_ENV_PATTERN = re.compile(r"\$\{(\w+)(?::-(.*?))?\}")


def substitute_env(value: str) -> str:
    """Replace ${VAR} and ${VAR:-default} in a string."""

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        env_val = os.environ.get(var_name)
        if env_val is not None:
            return env_val
        if default is not None:
            return default
        return match.group(0)  # Leave unreplaced

    return _ENV_PATTERN.sub(replacer, value)


def substitute_dict(data: dict[str, object]) -> dict[str, object]:
    """Recursively substitute env vars in a config dict."""
    result: dict[str, object] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = substitute_env(value)
        elif isinstance(value, dict):
            result[key] = substitute_dict(value)  # type: ignore[arg-type]
        elif isinstance(value, list):
            result[key] = [substitute_env(v) if isinstance(v, str) else v for v in value]
        else:
            result[key] = value
    return result
