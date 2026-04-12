"""Per-channel plugin system with allowlists and command gating."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ChannelPluginConfig:
    channel: str
    allowed_commands: set[str] = field(default_factory=set)
    blocked_commands: set[str] = field(default_factory=set)
    allowlist: set[str] = field(default_factory=set)
    blocklist: set[str] = field(default_factory=set)


class ChannelPluginManager:
    """Manages per-channel plugin configurations and command gating."""

    def __init__(self) -> None:
        self._configs: dict[str, ChannelPluginConfig] = {}

    def configure(self, config: ChannelPluginConfig) -> None:
        self._configs[config.channel] = config

    def get_config(self, channel: str) -> ChannelPluginConfig | None:
        return self._configs.get(channel)

    def is_command_allowed(self, channel: str, command: str) -> bool:
        config = self._configs.get(channel)
        if not config:
            return True
        if config.blocked_commands and command in config.blocked_commands:
            return False
        if config.allowed_commands and command not in config.allowed_commands:
            return False
        return True

    def is_user_allowed(self, channel: str, user_id: str) -> bool:
        config = self._configs.get(channel)
        if not config:
            return True
        if config.blocklist and user_id in config.blocklist:
            return False
        if config.allowlist and user_id not in config.allowlist:
            return False
        return True

    def list_channels(self) -> list[str]:
        return list(self._configs.keys())
