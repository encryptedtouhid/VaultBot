"""Unit tests for additional platform adapters."""

from __future__ import annotations

import pytest

from vaultbot.platforms.base import PlatformAdapter


class TestFeishuAdapter:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.feishu import FeishuAdapter

        adapter = FeishuAdapter(app_id="test", app_secret="test")
        assert adapter.platform_name == "feishu"

    def test_is_platform_adapter(self) -> None:
        from vaultbot.platforms.feishu import FeishuAdapter

        assert isinstance(FeishuAdapter(app_id="t", app_secret="t"), PlatformAdapter)

    @pytest.mark.asyncio
    async def test_healthcheck_before_connect(self) -> None:
        from vaultbot.platforms.feishu import FeishuAdapter

        adapter = FeishuAdapter(app_id="t", app_secret="t")
        assert await adapter.healthcheck() is False


class TestWeChatAdapter:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.wechat import WeChatAdapter

        adapter = WeChatAdapter(app_id="test", app_secret="test")
        assert adapter.platform_name == "wechat"

    def test_is_platform_adapter(self) -> None:
        from vaultbot.platforms.wechat import WeChatAdapter

        assert isinstance(WeChatAdapter(app_id="t", app_secret="t"), PlatformAdapter)

    @pytest.mark.asyncio
    async def test_healthcheck_before_connect(self) -> None:
        from vaultbot.platforms.wechat import WeChatAdapter

        adapter = WeChatAdapter(app_id="t", app_secret="t")
        assert await adapter.healthcheck() is False


class TestZaloAdapter:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.zalo import ZaloAdapter

        assert ZaloAdapter(access_token="t").platform_name == "zalo"

    def test_is_platform_adapter(self) -> None:
        from vaultbot.platforms.zalo import ZaloAdapter

        assert isinstance(ZaloAdapter(access_token="t"), PlatformAdapter)


class TestRocketChatAdapter:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.rocketchat import RocketChatAdapter

        adapter = RocketChatAdapter(
            server_url="https://rc.example.com", user_id="u", auth_token="t"
        )
        assert adapter.platform_name == "rocketchat"

    def test_is_platform_adapter(self) -> None:
        from vaultbot.platforms.rocketchat import RocketChatAdapter

        adapter = RocketChatAdapter(
            server_url="https://rc.example.com", user_id="u", auth_token="t"
        )
        assert isinstance(adapter, PlatformAdapter)


class TestZulipAdapter:
    def test_platform_name(self) -> None:
        from vaultbot.platforms.zulip import ZulipAdapter

        adapter = ZulipAdapter(server_url="https://z.example.com", email="bot@z.com", api_key="k")
        assert adapter.platform_name == "zulip"

    def test_is_platform_adapter(self) -> None:
        from vaultbot.platforms.zulip import ZulipAdapter

        adapter = ZulipAdapter(server_url="https://z.example.com", email="bot@z.com", api_key="k")
        assert isinstance(adapter, PlatformAdapter)
