"""Poll system for user voting and feedback collection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class PollType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    YES_NO = "yes_no"


@dataclass
class Poll:
    id: str
    question: str
    options: list[str]
    poll_type: PollType = PollType.SINGLE_CHOICE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    votes: dict[str, list[int]] = field(default_factory=dict)  # user_id -> option indices
    closed: bool = False

    def vote(self, user_id: str, option_indices: list[int]) -> bool:
        if self.closed:
            return False
        valid = [i for i in option_indices if 0 <= i < len(self.options)]
        if not valid:
            return False
        if self.poll_type == PollType.SINGLE_CHOICE:
            valid = valid[:1]
        self.votes[user_id] = valid
        return True

    def get_results(self) -> dict[str, int]:
        results: dict[str, int] = {opt: 0 for opt in self.options}
        for indices in self.votes.values():
            for i in indices:
                if 0 <= i < len(self.options):
                    results[self.options[i]] += 1
        return results

    @property
    def total_votes(self) -> int:
        return len(self.votes)

    def close(self) -> None:
        self.closed = True


class PollManager:
    def __init__(self) -> None:
        self._polls: dict[str, Poll] = {}
        self._counter: int = 0

    def create(self, question: str, options: list[str], poll_type: PollType = PollType.SINGLE_CHOICE) -> Poll:
        self._counter += 1
        poll = Poll(id=f"poll_{self._counter}", question=question, options=options, poll_type=poll_type)
        self._polls[poll.id] = poll
        return poll

    def get(self, poll_id: str) -> Poll | None:
        return self._polls.get(poll_id)

    def list_polls(self, *, active_only: bool = False) -> list[Poll]:
        polls = list(self._polls.values())
        if active_only:
            polls = [p for p in polls if not p.closed]
        return polls

    @property
    def count(self) -> int:
        return len(self._polls)
