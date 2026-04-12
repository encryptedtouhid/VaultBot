"""Unit tests for web UI dashboard."""

from __future__ import annotations

import pytest

from vaultbot.dashboard.web_ui import DashboardConfig, UITab, WebDashboard


class TestWebDashboard:
    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        dash = WebDashboard()
        await dash.start()
        assert dash.is_running is True
        await dash.stop()
        assert dash.is_running is False

    def test_switch_tab(self) -> None:
        dash = WebDashboard()
        dash.switch_tab(UITab.SETTINGS)
        assert dash.active_tab == UITab.SETTINGS

    def test_ws_connections(self) -> None:
        dash = WebDashboard()
        dash.add_ws_connection()
        assert dash.ws_connections == 1
        dash.remove_ws_connection()
        assert dash.ws_connections == 0

    def test_available_tabs(self) -> None:
        dash = WebDashboard()
        tabs = dash.get_available_tabs()
        assert UITab.CHAT in tabs
        assert UITab.LOGS in tabs

    def test_custom_config(self) -> None:
        config = DashboardConfig(port=3000, theme="light")
        dash = WebDashboard(config)
        assert dash.config.port == 3000
        assert dash.config.theme == "light"
