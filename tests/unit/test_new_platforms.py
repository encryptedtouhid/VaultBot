"""Tests for Slack, Teams, and iMessage platform adapters."""

from __future__ import annotations

import sys

import pytest


class TestSlackAdapter:
    """Test Slack adapter import guard and instantiation."""

    def test_import_guard(self) -> None:
        """Slack adapter module imports without crashing."""
        from vaultbot.platforms.slack import _SLACK_AVAILABLE

        # slack-bolt may or may not be installed
        assert isinstance(_SLACK_AVAILABLE, bool)

    def test_raises_without_slack_bolt(self) -> None:
        """If slack-bolt is not installed, clear error message."""
        from vaultbot.platforms.slack import _SLACK_AVAILABLE

        if not _SLACK_AVAILABLE:
            from vaultbot.platforms.slack import SlackAdapter

            with pytest.raises(ImportError, match="slack-bolt"):
                SlackAdapter(bot_token="xoxb-test", app_token="xapp-test")  # noqa: S106


class TestTeamsAdapter:
    """Test Teams adapter import guard and instantiation."""

    def test_import_guard(self) -> None:
        """Teams adapter module imports without crashing."""
        from vaultbot.platforms.teams import _TEAMS_AVAILABLE

        assert isinstance(_TEAMS_AVAILABLE, bool)

    def test_raises_without_botbuilder(self) -> None:
        """If botbuilder is not installed, clear error message."""
        from vaultbot.platforms.teams import _TEAMS_AVAILABLE

        if not _TEAMS_AVAILABLE:
            from vaultbot.platforms.teams import TeamsAdapter

            with pytest.raises(ImportError, match="botbuilder-core"):
                TeamsAdapter(app_id="test", app_password="test")  # noqa: S106


class TestIMessageAdapter:
    """Test iMessage adapter platform checks."""

    def test_import_succeeds(self) -> None:
        """iMessage adapter module imports without crashing."""
        from vaultbot.platforms.imessage import IMessageAdapter  # noqa: F401

    @pytest.mark.skipif(sys.platform == "darwin", reason="Only fails on non-macOS")
    def test_raises_on_non_macos(self) -> None:
        """iMessage adapter raises on non-macOS platforms."""
        from vaultbot.platforms.imessage import IMessageAdapter

        with pytest.raises(RuntimeError, match="macOS"):
            IMessageAdapter()

    @pytest.mark.skipif(sys.platform != "darwin", reason="Only runs on macOS")
    def test_creates_on_macos(self) -> None:
        """iMessage adapter creates successfully on macOS."""
        from vaultbot.platforms.imessage import IMessageAdapter

        adapter = IMessageAdapter()
        assert adapter.platform_name == "imessage"


class TestPlatformNames:
    """Verify all platform adapters have correct platform names."""

    def test_slack_platform_name(self) -> None:
        from vaultbot.platforms.slack import _SLACK_AVAILABLE

        if _SLACK_AVAILABLE:
            from vaultbot.platforms.slack import SlackAdapter

            adapter = SlackAdapter(bot_token="xoxb-test", app_token="xapp-test")  # noqa: S106
            assert adapter.platform_name == "slack"

    def test_teams_platform_name(self) -> None:
        from vaultbot.platforms.teams import _TEAMS_AVAILABLE

        if _TEAMS_AVAILABLE:
            from vaultbot.platforms.teams import TeamsAdapter

            adapter = TeamsAdapter(app_id="test", app_password="test")  # noqa: S106
            assert adapter.platform_name == "teams"

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_imessage_platform_name(self) -> None:
        from vaultbot.platforms.imessage import IMessageAdapter

        adapter = IMessageAdapter()
        assert adapter.platform_name == "imessage"
