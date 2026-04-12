"""Cross-platform poll normalization."""

from __future__ import annotations

from dataclasses import dataclass

_MIN_OPTIONS = 2
_MAX_OPTIONS = 10
_MAX_DURATION_HOURS = 168  # 1 week


@dataclass(frozen=True, slots=True)
class NormalizedPoll:
    question: str
    options: list[str]
    multi_select: bool = False
    max_selections: int = 1
    duration_seconds: int = 86400
    anonymous: bool = False


class PollValidationError(Exception):
    """Raised when poll validation fails."""


def validate_poll(
    question: str,
    options: list[str],
    multi_select: bool = False,
    max_selections: int = 1,
    duration_seconds: int = 86400,
) -> NormalizedPoll:
    """Validate and normalize a poll."""
    if not question.strip():
        raise PollValidationError("Question cannot be empty")
    if len(options) < _MIN_OPTIONS:
        raise PollValidationError(f"At least {_MIN_OPTIONS} options required")
    if len(options) > _MAX_OPTIONS:
        raise PollValidationError(f"Maximum {_MAX_OPTIONS} options allowed")
    if multi_select and max_selections > len(options):
        max_selections = len(options)
    if duration_seconds > _MAX_DURATION_HOURS * 3600:
        duration_seconds = _MAX_DURATION_HOURS * 3600
    if duration_seconds < 60:
        duration_seconds = 60

    return NormalizedPoll(
        question=question.strip(),
        options=[o.strip() for o in options],
        multi_select=multi_select,
        max_selections=max_selections,
        duration_seconds=duration_seconds,
    )


def format_for_platform(poll: NormalizedPoll, platform: str) -> dict[str, object]:
    """Format a poll for a specific platform."""
    if platform == "discord":
        return {
            "question": {"text": poll.question},
            "answers": [{"text": o} for o in poll.options],
            "duration": poll.duration_seconds // 3600 or 1,
            "allow_multiselect": poll.multi_select,
        }
    if platform == "telegram":
        return {
            "question": poll.question,
            "options": poll.options,
            "is_anonymous": poll.anonymous,
            "allows_multiple_answers": poll.multi_select,
        }
    # Generic format
    return {
        "question": poll.question,
        "options": poll.options,
        "multi_select": poll.multi_select,
        "duration_seconds": poll.duration_seconds,
    }
