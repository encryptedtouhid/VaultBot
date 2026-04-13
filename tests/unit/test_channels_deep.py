"""Unit tests for deep channel features."""

from __future__ import annotations

from vaultbot.platforms.capabilities import (
    PlatformCapability,
    get_capabilities,
    has_capability,
    supports_editing,
    supports_threads,
)
from vaultbot.platforms.chat_metadata import (
    ChatType,
    MentionMatcher,
    detect_chat_type,
    extract_mentions,
)


class TestChatMetadata:
    def test_extract_mentions_generic(self) -> None:
        mentions = extract_mentions("Hello @alice and @bob")
        assert "alice" in mentions
        assert "bob" in mentions

    def test_extract_mentions_discord(self) -> None:
        mentions = extract_mentions("Hey <@123456>!", "discord")
        assert "123456" in mentions

    def test_extract_mentions_slack(self) -> None:
        mentions = extract_mentions("Hi <@U123>", "slack")
        assert "U123" in mentions

    def test_detect_chat_type_dm(self) -> None:
        assert detect_chat_type(is_dm=True) == ChatType.DIRECT

    def test_detect_chat_type_thread(self) -> None:
        assert detect_chat_type(thread_id="t123") == ChatType.THREAD

    def test_detect_chat_type_channel(self) -> None:
        assert detect_chat_type() == ChatType.CHANNEL


class TestMentionMatcher:
    def test_bot_mentioned(self) -> None:
        matcher = MentionMatcher(bot_names=["vaultbot"])
        assert matcher.is_bot_mentioned("Hey @vaultbot help") is True

    def test_bot_not_mentioned(self) -> None:
        matcher = MentionMatcher(bot_names=["vaultbot"])
        assert matcher.is_bot_mentioned("Hello @alice") is False

    def test_add_bot_name(self) -> None:
        matcher = MentionMatcher()
        matcher.add_bot_name("mybot")
        assert matcher.is_bot_mentioned("@mybot do something") is True


class TestPlatformCapabilities:
    def test_discord_capabilities(self) -> None:
        caps = get_capabilities("discord")
        assert PlatformCapability.EDIT_MESSAGE in caps
        assert PlatformCapability.VOICE in caps

    def test_irc_limited(self) -> None:
        caps = get_capabilities("irc")
        assert PlatformCapability.EDIT_MESSAGE not in caps

    def test_has_capability(self) -> None:
        assert has_capability("telegram", PlatformCapability.POLLS) is True
        assert has_capability("irc", PlatformCapability.POLLS) is False

    def test_supports_editing(self) -> None:
        assert supports_editing("discord") is True
        assert supports_editing("irc") is False

    def test_supports_threads(self) -> None:
        assert supports_threads("slack") is True
        assert supports_threads("telegram") is False

    def test_unknown_platform(self) -> None:
        assert get_capabilities("unknown") == set()
