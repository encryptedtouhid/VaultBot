"""Unit tests for unified polls."""

from __future__ import annotations

import pytest

from vaultbot.tools.poll_normalization import (
    PollValidationError,
    format_for_platform,
    validate_poll,
)


class TestPollValidation:
    def test_valid_poll(self) -> None:
        poll = validate_poll("Fav color?", ["Red", "Blue", "Green"])
        assert poll.question == "Fav color?"
        assert len(poll.options) == 3

    def test_empty_question(self) -> None:
        with pytest.raises(PollValidationError, match="empty"):
            validate_poll("", ["A", "B"])

    def test_too_few_options(self) -> None:
        with pytest.raises(PollValidationError, match="At least"):
            validate_poll("Q?", ["Only one"])

    def test_too_many_options(self) -> None:
        with pytest.raises(PollValidationError, match="Maximum"):
            validate_poll("Q?", [f"opt{i}" for i in range(20)])

    def test_max_selections_clamped(self) -> None:
        poll = validate_poll("Q?", ["A", "B"], multi_select=True, max_selections=10)
        assert poll.max_selections == 2

    def test_duration_clamped(self) -> None:
        poll = validate_poll("Q?", ["A", "B"], duration_seconds=10)
        assert poll.duration_seconds == 60

    def test_multi_select(self) -> None:
        poll = validate_poll("Q?", ["A", "B", "C"], multi_select=True)
        assert poll.multi_select is True


class TestFormatForPlatform:
    def test_discord_format(self) -> None:
        poll = validate_poll("Q?", ["A", "B"])
        result = format_for_platform(poll, "discord")
        assert "question" in result
        assert "answers" in result

    def test_telegram_format(self) -> None:
        poll = validate_poll("Q?", ["A", "B"])
        result = format_for_platform(poll, "telegram")
        assert "options" in result

    def test_generic_format(self) -> None:
        poll = validate_poll("Q?", ["A", "B"])
        result = format_for_platform(poll, "unknown")
        assert result["question"] == "Q?"
