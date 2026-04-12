"""Inbound message debounce and coalescing."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DebounceConfig:
    delay_ms: int = 1500
    max_wait_ms: int = 5000
    enabled: bool = True


@dataclass(slots=True)
class PendingBatch:
    messages: list[str] = field(default_factory=list)
    first_received: float = field(default_factory=time.time)
    last_received: float = field(default_factory=time.time)


def looks_incomplete(text: str) -> bool:
    """Heuristic check if a message looks incomplete."""
    stripped = text.rstrip()
    if not stripped:
        return False
    return stripped.endswith(("...", ",", " and", " or", " but", " the", " a"))


def coalesce_messages(messages: list[str]) -> str:
    """Merge multiple messages into one."""
    # Deduplicate consecutive duplicates
    deduped: list[str] = []
    for msg in messages:
        if not deduped or msg != deduped[-1]:
            deduped.append(msg)
    return "\n".join(deduped)


class DebounceEngine:
    """Debounce and coalesce rapid inbound messages."""

    def __init__(self, config: DebounceConfig | None = None) -> None:
        self._config = config or DebounceConfig()
        self._batches: dict[str, PendingBatch] = {}

    @property
    def config(self) -> DebounceConfig:
        return self._config

    @property
    def pending_count(self) -> int:
        return len(self._batches)

    def add_message(self, key: str, text: str) -> bool:
        """Add a message to the debounce buffer.

        Returns True if the batch should be flushed.
        """
        if not self._config.enabled:
            return True  # Immediately flush

        now = time.time()
        batch = self._batches.get(key)
        if batch is None:
            self._batches[key] = PendingBatch(
                messages=[text], first_received=now, last_received=now
            )
            return False

        batch.messages.append(text)
        batch.last_received = now

        # Check max wait
        elapsed_ms = (now - batch.first_received) * 1000
        if elapsed_ms >= self._config.max_wait_ms:
            return True

        return False

    def should_flush(self, key: str) -> bool:
        """Check if a batch should be flushed based on delay."""
        batch = self._batches.get(key)
        if not batch:
            return False
        elapsed_ms = (time.time() - batch.last_received) * 1000
        return elapsed_ms >= self._config.delay_ms

    def flush(self, key: str) -> str | None:
        """Flush a batch, returning the coalesced message."""
        batch = self._batches.pop(key, None)
        if not batch:
            return None
        return coalesce_messages(batch.messages)

    def flush_all(self) -> dict[str, str]:
        """Flush all pending batches."""
        results: dict[str, str] = {}
        for key in list(self._batches.keys()):
            msg = self.flush(key)
            if msg:
                results[key] = msg
        return results
