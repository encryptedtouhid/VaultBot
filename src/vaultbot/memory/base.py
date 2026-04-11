"""Abstract memory store protocol for persistent conversation storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """A single turn in a conversation (user message + assistant response)."""

    chat_id: str
    user_message: str
    assistant_response: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UserPreferences:
    """Stored preferences for a user."""

    user_id: str
    platform: str
    preferences: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class MemoryStore(Protocol):
    """Protocol for persistent memory backends."""

    async def save_turn(self, turn: ConversationTurn) -> None:
        """Save a conversation turn."""
        ...

    async def get_history(
        self, chat_id: str, *, limit: int = 20
    ) -> list[ConversationTurn]:
        """Retrieve conversation history for a chat."""
        ...

    async def save_summary(self, chat_id: str, summary: str) -> None:
        """Save a conversation summary."""
        ...

    async def get_summary(self, chat_id: str) -> str | None:
        """Get the latest conversation summary."""
        ...

    async def save_user_preferences(self, prefs: UserPreferences) -> None:
        """Save user preferences."""
        ...

    async def get_user_preferences(
        self, user_id: str, platform: str
    ) -> UserPreferences | None:
        """Get user preferences."""
        ...

    async def close(self) -> None:
        """Close the store connection."""
        ...
