"""Pluggable context engine with registry and lifecycle methods."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from vaultbot.core.message import ChatMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AssembleResult:
    """Result of assembling messages for a model turn."""

    messages: list[ChatMessage]
    token_count: int = 0
    truncated: bool = False
    cache_hit: bool = False


@runtime_checkable
class ContextEngine(Protocol):
    """Protocol for pluggable context engine implementations."""

    async def bootstrap(self, session_id: str) -> None:
        """Initialize session state."""
        ...

    async def ingest(self, session_id: str, message: ChatMessage) -> None:
        """Store a new message."""
        ...

    async def assemble(self, session_id: str, token_budget: int) -> AssembleResult:
        """Prepare messages for a model turn within token budget."""
        ...

    async def compact(self, session_id: str) -> int:
        """Reduce token usage via summarization/pruning. Returns tokens freed."""
        ...

    async def after_turn(self, session_id: str) -> None:
        """Post-turn cleanup/maintenance."""
        ...


class InMemoryContextEngine:
    """Simple in-memory context engine implementation."""

    def __init__(self, max_messages: int = 100) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._max_messages = max_messages

    async def bootstrap(self, session_id: str) -> None:
        self._sessions.setdefault(session_id, [])

    async def ingest(self, session_id: str, message: ChatMessage) -> None:
        messages = self._sessions.setdefault(session_id, [])
        messages.append(message)
        if len(messages) > self._max_messages:
            messages.pop(0)

    async def assemble(self, session_id: str, token_budget: int) -> AssembleResult:
        messages = self._sessions.get(session_id, [])
        selected: list[ChatMessage] = []
        total_tokens = 0
        for msg in reversed(messages):
            est = len(msg.content) // 4
            if total_tokens + est > token_budget:
                return AssembleResult(
                    messages=list(reversed(selected)),
                    token_count=total_tokens,
                    truncated=True,
                )
            selected.append(msg)
            total_tokens += est
        return AssembleResult(messages=list(reversed(selected)), token_count=total_tokens)

    async def compact(self, session_id: str) -> int:
        messages = self._sessions.get(session_id, [])
        if len(messages) <= 10:
            return 0
        removed = messages[: len(messages) - 10]
        self._sessions[session_id] = messages[-10:]
        freed = sum(len(m.content) // 4 for m in removed)
        return freed

    async def after_turn(self, session_id: str) -> None:
        pass

    def message_count(self, session_id: str) -> int:
        return len(self._sessions.get(session_id, []))


ContextEngineFactory = Callable[[], ContextEngine]


class ContextEngineRegistry:
    """Registry for context engine factories."""

    def __init__(self) -> None:
        self._factories: dict[str, ContextEngineFactory] = {}
        self._default: str = ""

    def register(self, name: str, factory: ContextEngineFactory) -> None:
        self._factories[name] = factory
        if not self._default:
            self._default = name

    def create(self, name: str = "") -> ContextEngine:
        engine_name = name or self._default
        factory = self._factories.get(engine_name)
        if not factory:
            raise ValueError(f"Unknown context engine: {engine_name}")
        return factory()

    def list_engines(self) -> list[str]:
        return list(self._factories.keys())
