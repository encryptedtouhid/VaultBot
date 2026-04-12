"""Advanced context window management."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class RetentionStrategy(str, Enum):
    FIFO = "fifo"
    PRIORITY = "priority"
    RELEVANCE = "relevance"


@dataclass(frozen=True, slots=True)
class WindowConfig:
    max_tokens: int = 8192
    strategy: RetentionStrategy = RetentionStrategy.FIFO
    reserve_tokens: int = 1024


@dataclass(slots=True)
class ContextEntry:
    content: str
    role: str = "user"
    token_count: int = 0
    priority: int = 0
    relevance: float = 0.0


class ContextWindowManager:
    """Manages context window with configurable retention strategies."""

    def __init__(self, config: WindowConfig | None = None) -> None:
        self._config = config or WindowConfig()
        self._entries: list[ContextEntry] = []
        self._total_tokens = 0

    @property
    def config(self) -> WindowConfig:
        return self._config

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def add(
        self, content: str, role: str = "user", priority: int = 0, relevance: float = 0.0
    ) -> None:
        tokens = self._estimate_tokens(content)
        entry = ContextEntry(
            content=content,
            role=role,
            token_count=tokens,
            priority=priority,
            relevance=relevance,
        )
        self._entries.append(entry)
        self._total_tokens += tokens
        self._trim()

    def get_window(self) -> list[ContextEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self._total_tokens = 0

    def _trim(self) -> None:
        budget = self._config.max_tokens - self._config.reserve_tokens
        while self._total_tokens > budget and self._entries:
            if self._config.strategy == RetentionStrategy.FIFO:
                removed = self._entries.pop(0)
            elif self._config.strategy == RetentionStrategy.PRIORITY:
                idx = min(range(len(self._entries)), key=lambda i: self._entries[i].priority)
                removed = self._entries.pop(idx)
            else:
                idx = min(range(len(self._entries)), key=lambda i: self._entries[i].relevance)
                removed = self._entries.pop(idx)
            self._total_tokens -= removed.token_count

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)
