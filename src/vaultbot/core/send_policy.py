"""Per-session send policy with rate limiting and size constraints."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SendPolicyConfig:
    max_messages_per_minute: int = 30
    max_response_tokens: int = 8192
    max_response_bytes: int = 100_000
    throttle_delay_ms: int = 0


class SendPolicy:
    """Enforces per-session send policies."""

    def __init__(self, config: SendPolicyConfig | None = None) -> None:
        self._config = config or SendPolicyConfig()
        self._send_times: list[float] = []

    @property
    def config(self) -> SendPolicyConfig:
        return self._config

    def check_rate(self) -> bool:
        """Check if sending is within rate limits."""
        now = time.time()
        self._send_times = [t for t in self._send_times if now - t < 60]
        return len(self._send_times) < self._config.max_messages_per_minute

    def record_send(self) -> None:
        self._send_times.append(time.time())

    def check_size(self, content: str) -> bool:
        """Check if content is within size limits."""
        return len(content.encode()) <= self._config.max_response_bytes

    def check_tokens(self, token_count: int) -> bool:
        return token_count <= self._config.max_response_tokens


@dataclass(frozen=True, slots=True)
class ModelOverride:
    """Per-session model override."""

    model: str = ""
    temperature: float | None = None
    max_tokens: int | None = None

    @property
    def is_set(self) -> bool:
        return bool(self.model)


class ModelOverrideManager:
    """Manages per-session model overrides."""

    def __init__(self) -> None:
        self._overrides: dict[str, ModelOverride] = {}

    def set_override(self, session_id: str, override: ModelOverride) -> None:
        self._overrides[session_id] = override

    def get_override(self, session_id: str) -> ModelOverride | None:
        return self._overrides.get(session_id)

    def clear_override(self, session_id: str) -> bool:
        if session_id in self._overrides:
            del self._overrides[session_id]
            return True
        return False

    def has_override(self, session_id: str) -> bool:
        override = self._overrides.get(session_id)
        return override is not None and override.is_set
