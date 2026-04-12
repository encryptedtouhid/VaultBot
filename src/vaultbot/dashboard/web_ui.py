"""Web-based control UI dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class UITab(str, Enum):
    CHAT = "chat"
    GATEWAY = "gateway"
    SETTINGS = "settings"
    CRON = "cron"
    LOGS = "logs"
    SESSIONS = "sessions"


@dataclass(frozen=True, slots=True)
class DashboardConfig:
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8080
    theme: str = "dark"
    auth_required: bool = True


class WebDashboard:
    """Web-based control UI with real-time updates."""

    def __init__(self, config: DashboardConfig | None = None) -> None:
        self._config = config or DashboardConfig()
        self._running = False
        self._active_tab = UITab.CHAT
        self._ws_connections = 0

    @property
    def config(self) -> DashboardConfig:
        return self._config

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def active_tab(self) -> UITab:
        return self._active_tab

    @property
    def ws_connections(self) -> int:
        return self._ws_connections

    async def start(self) -> None:
        self._running = True
        logger.info("web_ui_started", port=self._config.port)

    async def stop(self) -> None:
        self._running = False
        self._ws_connections = 0

    def switch_tab(self, tab: UITab) -> None:
        self._active_tab = tab

    def add_ws_connection(self) -> None:
        self._ws_connections += 1

    def remove_ws_connection(self) -> None:
        if self._ws_connections > 0:
            self._ws_connections -= 1

    def get_available_tabs(self) -> list[UITab]:
        return list(UITab)
