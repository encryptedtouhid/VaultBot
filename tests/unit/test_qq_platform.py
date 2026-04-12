"""Unit tests for QQ Bot platform."""

from __future__ import annotations

import pytest

from vaultbot.platforms.base import PlatformAdapter
from vaultbot.platforms.qq import QQBotAdapter


class TestQQBotAdapter:
    def test_platform_name(self) -> None:
        adapter = QQBotAdapter(app_id="test", app_secret="test")
        assert adapter.platform_name == "qq"

    def test_is_platform_adapter(self) -> None:
        adapter = QQBotAdapter(app_id="t", app_secret="t")
        assert isinstance(adapter, PlatformAdapter)

    @pytest.mark.asyncio
    async def test_healthcheck_before_connect(self) -> None:
        adapter = QQBotAdapter(app_id="t", app_secret="t")
        assert await adapter.healthcheck() is False

    def test_sandbox_mode(self) -> None:
        adapter = QQBotAdapter(app_id="t", app_secret="t", sandbox=True)
        assert adapter.platform_name == "qq"
