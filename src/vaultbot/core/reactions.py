"""Cross-platform message reaction handling."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ReactionType(str, Enum):
    EMOJI = "emoji"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class Reaction:
    emoji: str
    user_id: str
    message_id: str
    platform: str
    reaction_type: ReactionType = ReactionType.EMOJI
    timestamp: float = field(default_factory=time.time)


# Platform-specific emoji normalization
_EMOJI_ALIASES: dict[str, str] = {
    ":thumbsup:": "\U0001f44d",
    ":heart:": "\u2764\ufe0f",
    ":fire:": "\U0001f525",
    ":100:": "\U0001f4af",
    ":eyes:": "\U0001f440",
    ":rocket:": "\U0001f680",
    "+1": "\U0001f44d",
    "-1": "\U0001f44e",
}


def normalize_emoji(emoji: str) -> str:
    """Normalize platform-specific emoji representations."""
    return _EMOJI_ALIASES.get(emoji, emoji)


class ReactionManager:
    """Manages cross-platform message reactions."""

    def __init__(self) -> None:
        self._reactions: dict[str, list[Reaction]] = {}

    def add_reaction(
        self,
        message_id: str,
        emoji: str,
        user_id: str,
        platform: str,
    ) -> Reaction:
        normalized = normalize_emoji(emoji)
        reaction = Reaction(
            emoji=normalized,
            user_id=user_id,
            message_id=message_id,
            platform=platform,
        )
        self._reactions.setdefault(message_id, []).append(reaction)
        logger.info("reaction_added", message_id=message_id, emoji=normalized)
        return reaction

    def remove_reaction(self, message_id: str, emoji: str, user_id: str) -> bool:
        normalized = normalize_emoji(emoji)
        reactions = self._reactions.get(message_id, [])
        for i, r in enumerate(reactions):
            if r.emoji == normalized and r.user_id == user_id:
                reactions.pop(i)
                return True
        return False

    def get_reactions(self, message_id: str) -> list[Reaction]:
        return list(self._reactions.get(message_id, []))

    def get_reaction_counts(self, message_id: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._reactions.get(message_id, []):
            counts[r.emoji] = counts.get(r.emoji, 0) + 1
        return counts

    def clear_reactions(self, message_id: str) -> None:
        self._reactions.pop(message_id, None)
