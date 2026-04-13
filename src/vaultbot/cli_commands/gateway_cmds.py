"""Gateway management CLI commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GatewayStatus:
    host: str = ""
    port: int = 0
    connected: bool = False
    clients: int = 0
    uptime_seconds: float = 0.0


class GatewayCommands:
    """CLI commands for gateway management."""

    def __init__(self) -> None:
        self._connected = False
        self._url = ""

    def connect(self, url: str) -> bool:
        self._url = url
        self._connected = True
        return True

    def disconnect(self) -> bool:
        if not self._connected:
            return False
        self._connected = False
        self._url = ""
        return True

    def status(self) -> GatewayStatus:
        return GatewayStatus(connected=self._connected)

    @property
    def is_connected(self) -> bool:
        return self._connected
