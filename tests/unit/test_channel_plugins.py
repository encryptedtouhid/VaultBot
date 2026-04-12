"""Unit tests for channel plugin system."""

from __future__ import annotations

from vaultbot.platforms.channel_plugins import ChannelPluginConfig, ChannelPluginManager


class TestChannelPluginManager:
    def test_configure(self) -> None:
        mgr = ChannelPluginManager()
        mgr.configure(ChannelPluginConfig(channel="general"))
        assert "general" in mgr.list_channels()

    def test_command_allowed_default(self) -> None:
        mgr = ChannelPluginManager()
        assert mgr.is_command_allowed("any", "help") is True

    def test_command_blocked(self) -> None:
        mgr = ChannelPluginManager()
        mgr.configure(ChannelPluginConfig(channel="gen", blocked_commands={"admin"}))
        assert mgr.is_command_allowed("gen", "admin") is False
        assert mgr.is_command_allowed("gen", "help") is True

    def test_command_allowlist(self) -> None:
        mgr = ChannelPluginManager()
        mgr.configure(ChannelPluginConfig(channel="gen", allowed_commands={"help", "status"}))
        assert mgr.is_command_allowed("gen", "help") is True
        assert mgr.is_command_allowed("gen", "admin") is False

    def test_user_allowed_default(self) -> None:
        mgr = ChannelPluginManager()
        assert mgr.is_user_allowed("any", "user1") is True

    def test_user_blocklist(self) -> None:
        mgr = ChannelPluginManager()
        mgr.configure(ChannelPluginConfig(channel="gen", blocklist={"spammer"}))
        assert mgr.is_user_allowed("gen", "spammer") is False
        assert mgr.is_user_allowed("gen", "normal") is True

    def test_user_allowlist(self) -> None:
        mgr = ChannelPluginManager()
        mgr.configure(ChannelPluginConfig(channel="vip", allowlist={"admin1"}))
        assert mgr.is_user_allowed("vip", "admin1") is True
        assert mgr.is_user_allowed("vip", "other") is False
