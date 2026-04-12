"""Presence and typing indicators across platforms."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class PresenceState(str, Enum):
    """User/bot presence state."""

    ONLINE = "online"
    IDLE = "idle"
    DO_NOT_DISTURB = "dnd"
    OFFLINE = "offline"


class TypingState(str, Enum):
    """Typing indicator state."""

    IDLE = "idle"
    TYPING = "typing"


@dataclass(slots=True)
class PresenceInfo:
    """Presence information for a user or bot."""

    entity_id: str
    platform: str
    state: PresenceState = PresenceState.OFFLINE
    last_seen: float = field(default_factory=time.time)
    status_text: str = ""


@dataclass(frozen=True, slots=True)
class TypingConfig:
    """Per-platform typing indicator configuration."""

    enabled: bool = True
    refresh_interval_seconds: float = 5.0
    auto_stop_seconds: float = 30.0


class PresenceManager:
    """Manages presence state and typing indicators across platforms."""

    def __init__(self) -> None:
        self._presence: dict[str, PresenceInfo] = {}
        self._typing: dict[str, TypingState] = {}
        self._platform_config: dict[str, TypingConfig] = {}

    def set_presence(
        self, entity_id: str, platform: str, state: PresenceState, status_text: str = ""
    ) -> PresenceInfo:
        key = f"{platform}:{entity_id}"
        info = PresenceInfo(
            entity_id=entity_id,
            platform=platform,
            state=state,
            last_seen=time.time(),
            status_text=status_text,
        )
        self._presence[key] = info
        logger.info("presence_updated", entity=key, state=state.value)
        return info

    def get_presence(self, entity_id: str, platform: str) -> PresenceInfo | None:
        return self._presence.get(f"{platform}:{entity_id}")

    def set_typing(self, entity_id: str, platform: str, state: TypingState) -> None:
        key = f"{platform}:{entity_id}"
        self._typing[key] = state

    def get_typing(self, entity_id: str, platform: str) -> TypingState:
        return self._typing.get(f"{platform}:{entity_id}", TypingState.IDLE)

    def configure_platform(self, platform: str, config: TypingConfig) -> None:
        self._platform_config[platform] = config

    def get_platform_config(self, platform: str) -> TypingConfig:
        return self._platform_config.get(platform, TypingConfig())

    def is_typing_supported(self, platform: str) -> bool:
        """Check if typing indicators are supported for a platform."""
        supported = {"telegram", "discord", "slack", "whatsapp", "teams", "matrix", "mattermost"}
        return platform in supported

    def list_online(self, platform: str | None = None) -> list[PresenceInfo]:
        """List all online entities, optionally filtered by platform."""
        return [
            p
            for p in self._presence.values()
            if p.state == PresenceState.ONLINE and (platform is None or p.platform == platform)
        ]
