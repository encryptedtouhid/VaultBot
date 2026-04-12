"""Unit tests for presence and typing indicators."""

from __future__ import annotations

from vaultbot.core.presence import (
    PresenceManager,
    PresenceState,
    TypingConfig,
    TypingState,
)


class TestPresenceManager:
    def test_set_and_get_presence(self) -> None:
        mgr = PresenceManager()
        info = mgr.set_presence("user1", "telegram", PresenceState.ONLINE, "Working")
        assert info.state == PresenceState.ONLINE
        assert info.status_text == "Working"
        loaded = mgr.get_presence("user1", "telegram")
        assert loaded is not None

    def test_get_missing_presence(self) -> None:
        mgr = PresenceManager()
        assert mgr.get_presence("nope", "telegram") is None

    def test_set_and_get_typing(self) -> None:
        mgr = PresenceManager()
        mgr.set_typing("user1", "discord", TypingState.TYPING)
        assert mgr.get_typing("user1", "discord") == TypingState.TYPING

    def test_typing_default_idle(self) -> None:
        mgr = PresenceManager()
        assert mgr.get_typing("user1", "telegram") == TypingState.IDLE

    def test_configure_platform(self) -> None:
        mgr = PresenceManager()
        config = TypingConfig(enabled=False, refresh_interval_seconds=10.0)
        mgr.configure_platform("irc", config)
        assert mgr.get_platform_config("irc").enabled is False

    def test_default_platform_config(self) -> None:
        mgr = PresenceManager()
        config = mgr.get_platform_config("unknown")
        assert config.enabled is True

    def test_is_typing_supported(self) -> None:
        mgr = PresenceManager()
        assert mgr.is_typing_supported("telegram") is True
        assert mgr.is_typing_supported("irc") is False

    def test_list_online(self) -> None:
        mgr = PresenceManager()
        mgr.set_presence("u1", "telegram", PresenceState.ONLINE)
        mgr.set_presence("u2", "telegram", PresenceState.OFFLINE)
        mgr.set_presence("u3", "discord", PresenceState.ONLINE)
        online = mgr.list_online()
        assert len(online) == 2
        online_tg = mgr.list_online("telegram")
        assert len(online_tg) == 1
