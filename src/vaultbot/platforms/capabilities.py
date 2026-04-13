"""Platform capability detection."""

from __future__ import annotations

from enum import Enum


class PlatformCapability(str, Enum):
    EDIT_MESSAGE = "edit_message"
    DELETE_MESSAGE = "delete_message"
    REACTIONS = "reactions"
    THREADS = "threads"
    TYPING_INDICATOR = "typing_indicator"
    FILE_UPLOAD = "file_upload"
    RICH_TEXT = "rich_text"
    BUTTONS = "buttons"
    EMBEDS = "embeds"
    VOICE = "voice"
    POLLS = "polls"


# Per-platform capability map
_PLATFORM_CAPABILITIES: dict[str, set[PlatformCapability]] = {
    "discord": {
        PlatformCapability.EDIT_MESSAGE,
        PlatformCapability.DELETE_MESSAGE,
        PlatformCapability.REACTIONS,
        PlatformCapability.THREADS,
        PlatformCapability.TYPING_INDICATOR,
        PlatformCapability.FILE_UPLOAD,
        PlatformCapability.RICH_TEXT,
        PlatformCapability.BUTTONS,
        PlatformCapability.EMBEDS,
        PlatformCapability.VOICE,
        PlatformCapability.POLLS,
    },
    "slack": {
        PlatformCapability.EDIT_MESSAGE,
        PlatformCapability.DELETE_MESSAGE,
        PlatformCapability.REACTIONS,
        PlatformCapability.THREADS,
        PlatformCapability.TYPING_INDICATOR,
        PlatformCapability.FILE_UPLOAD,
        PlatformCapability.RICH_TEXT,
        PlatformCapability.BUTTONS,
    },
    "telegram": {
        PlatformCapability.EDIT_MESSAGE,
        PlatformCapability.DELETE_MESSAGE,
        PlatformCapability.REACTIONS,
        PlatformCapability.TYPING_INDICATOR,
        PlatformCapability.FILE_UPLOAD,
        PlatformCapability.RICH_TEXT,
        PlatformCapability.BUTTONS,
        PlatformCapability.POLLS,
    },
    "irc": {
        PlatformCapability.RICH_TEXT,
    },
    "matrix": {
        PlatformCapability.EDIT_MESSAGE,
        PlatformCapability.REACTIONS,
        PlatformCapability.THREADS,
        PlatformCapability.TYPING_INDICATOR,
        PlatformCapability.FILE_UPLOAD,
        PlatformCapability.RICH_TEXT,
    },
}


def get_capabilities(platform: str) -> set[PlatformCapability]:
    """Get capabilities for a platform."""
    return _PLATFORM_CAPABILITIES.get(platform, set())


def has_capability(platform: str, capability: PlatformCapability) -> bool:
    """Check if a platform has a specific capability."""
    return capability in get_capabilities(platform)


def supports_editing(platform: str) -> bool:
    return has_capability(platform, PlatformCapability.EDIT_MESSAGE)


def supports_threads(platform: str) -> bool:
    return has_capability(platform, PlatformCapability.THREADS)
