"""Canvas HTTP server with WebSocket support."""

from __future__ import annotations

from dataclasses import dataclass

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CanvasConfig:
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 9090
    static_dir: str = ""
    live_reload: bool = False


class CanvasServer:
    """HTTP server for canvas/web UI with WebSocket support."""

    def __init__(self, config: CanvasConfig | None = None) -> None:
        self._config = config or CanvasConfig()
        self._running = False
        self._connections = 0

    @property
    def config(self) -> CanvasConfig:
        return self._config

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def connection_count(self) -> int:
        return self._connections

    async def start(self) -> None:
        self._running = True
        logger.info("canvas_started", host=self._config.host, port=self._config.port)

    async def stop(self) -> None:
        self._running = False
        self._connections = 0

    def add_connection(self) -> None:
        self._connections += 1

    def remove_connection(self) -> None:
        if self._connections > 0:
            self._connections -= 1
