"""Channel management CLI commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChannelStatus:
    name: str
    enabled: bool
    connected: bool = False
    message_count: int = 0


class ChannelCommands:
    """CLI commands for channel management."""

    def __init__(self) -> None:
        self._channels: dict[str, ChannelStatus] = {}

    def add(self, name: str) -> ChannelStatus:
        status = ChannelStatus(name=name, enabled=True)
        self._channels[name] = status
        return status

    def remove(self, name: str) -> bool:
        if name in self._channels:
            del self._channels[name]
            return True
        return False

    def status(self, name: str) -> ChannelStatus | None:
        return self._channels.get(name)

    def list_channels(self) -> list[ChannelStatus]:
        return list(self._channels.values())

    def enable(self, name: str) -> bool:
        if name in self._channels:
            self._channels[name] = ChannelStatus(
                name=name, enabled=True, connected=self._channels[name].connected
            )
            return True
        return False

    def disable(self, name: str) -> bool:
        if name in self._channels:
            self._channels[name] = ChannelStatus(name=name, enabled=False)
            return True
        return False
