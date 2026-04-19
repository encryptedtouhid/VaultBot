"""Chat metadata enrichment and mention detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ChatType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    THREAD = "thread"
    CHANNEL = "channel"


@dataclass(frozen=True, slots=True)
class ChatMetadata:
    """Enriched metadata for a chat message."""

    chat_type: ChatType = ChatType.CHANNEL
    thread_id: str = ""
    reply_to_id: str = ""
    is_forwarded: bool = False
    is_edited: bool = False
    mentions: list[str] = field(default_factory=list)
    platform: str = ""


_MENTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "discord": re.compile(r"<@!?(\d+)>"),
    "slack": re.compile(r"<@(\w+)>"),
    "telegram": re.compile(r"@(\w+)"),
    "generic": re.compile(r"@(\w+)"),
}


def extract_mentions(text: str, platform: str = "generic") -> list[str]:
    """Extract @mentions from text using platform-specific patterns."""
    pattern = _MENTION_PATTERNS.get(platform, _MENTION_PATTERNS["generic"])
    return pattern.findall(text)


def detect_chat_type(is_dm: bool = False, thread_id: str = "", channel_name: str = "") -> ChatType:
    """Detect chat type from message context."""
    if is_dm:
        return ChatType.DIRECT
    if thread_id:
        return ChatType.THREAD
    return ChatType.CHANNEL


class MentionMatcher:
    """Matches mentions against allowlists and patterns."""

    def __init__(self, bot_names: list[str] | None = None) -> None:
        self._bot_names = {n.lower() for n in (bot_names or ["vaultbot"])}

    def is_bot_mentioned(self, text: str, platform: str = "generic") -> bool:
        mentions = extract_mentions(text, platform)
        return any(m.lower() in self._bot_names for m in mentions)

    def add_bot_name(self, name: str) -> None:
        self._bot_names.add(name.lower())
