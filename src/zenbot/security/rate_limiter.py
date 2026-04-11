"""Token bucket rate limiter for per-user and global request throttling."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from zenbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """A single token bucket for rate limiting."""

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self.last_refill = time.monotonic()

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens. Returns True if allowed, False if rate limited."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def time_until_available(self) -> float:
        """Seconds until at least 1 token is available."""
        if self.tokens >= 1.0:
            return 0.0
        if self.refill_rate <= 0:
            return float("inf")
        return (1.0 - self.tokens) / self.refill_rate


class RateLimiter:
    """Per-user and global rate limiting using token buckets."""

    def __init__(
        self,
        *,
        user_capacity: float = 10.0,
        user_refill_rate: float = 1.0,
        global_capacity: float = 50.0,
        global_refill_rate: float = 10.0,
    ) -> None:
        self._user_buckets: dict[str, TokenBucket] = {}
        self._user_capacity = user_capacity
        self._user_refill_rate = user_refill_rate
        self._global_bucket = TokenBucket(
            capacity=global_capacity, refill_rate=global_refill_rate
        )

    def _get_user_bucket(self, user_id: str) -> TokenBucket:
        """Get or create a token bucket for a user."""
        if user_id not in self._user_buckets:
            self._user_buckets[user_id] = TokenBucket(
                capacity=self._user_capacity,
                refill_rate=self._user_refill_rate,
            )
        return self._user_buckets[user_id]

    def is_allowed(self, user_id: str) -> bool:
        """Check if a request from this user is allowed.

        Checks both user-level and global rate limits.
        """
        user_bucket = self._get_user_bucket(user_id)

        if not self._global_bucket.consume():
            logger.warning("rate_limited", user_id=user_id, scope="global")
            return False

        if not user_bucket.consume():
            logger.warning("rate_limited", user_id=user_id, scope="user")
            return False

        return True

    def time_until_allowed(self, user_id: str) -> float:
        """Get seconds until the user can make another request."""
        user_bucket = self._get_user_bucket(user_id)
        return max(
            user_bucket.time_until_available,
            self._global_bucket.time_until_available,
        )

    def cleanup_stale_buckets(self, max_age_seconds: float = 3600.0) -> int:
        """Remove user buckets that haven't been used recently."""
        now = time.monotonic()
        stale = [
            uid
            for uid, bucket in self._user_buckets.items()
            if now - bucket.last_refill > max_age_seconds
        ]
        for uid in stale:
            del self._user_buckets[uid]
        return len(stale)
