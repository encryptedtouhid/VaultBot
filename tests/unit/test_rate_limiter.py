"""Tests for the rate limiter module."""

from vaultbot.security.rate_limiter import RateLimiter, TokenBucket


def test_token_bucket_allows_within_capacity() -> None:
    bucket = TokenBucket(capacity=5.0, refill_rate=1.0)
    for _ in range(5):
        assert bucket.consume() is True


def test_token_bucket_rejects_over_capacity() -> None:
    bucket = TokenBucket(capacity=2.0, refill_rate=0.0)  # No refill
    assert bucket.consume() is True
    assert bucket.consume() is True
    assert bucket.consume() is False


def test_rate_limiter_allows_normal_usage() -> None:
    limiter = RateLimiter(user_capacity=5.0, user_refill_rate=1.0)
    for _ in range(5):
        assert limiter.is_allowed("user1") is True


def test_rate_limiter_blocks_excessive_usage() -> None:
    limiter = RateLimiter(
        user_capacity=2.0,
        user_refill_rate=0.0,
        global_capacity=100.0,
        global_refill_rate=100.0,
    )
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is False


def test_rate_limiter_per_user_isolation() -> None:
    limiter = RateLimiter(
        user_capacity=1.0,
        user_refill_rate=0.0,
        global_capacity=100.0,
        global_refill_rate=100.0,
    )
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is False
    # Different user should still be allowed
    assert limiter.is_allowed("user2") is True


def test_time_until_allowed() -> None:
    limiter = RateLimiter(user_capacity=1.0, user_refill_rate=1.0)
    limiter.is_allowed("user1")  # consume the token
    wait = limiter.time_until_allowed("user1")
    assert wait >= 0.0


def test_cleanup_stale_buckets() -> None:
    limiter = RateLimiter()
    limiter.is_allowed("user1")
    limiter.is_allowed("user2")
    # With max_age=0, all buckets are stale
    removed = limiter.cleanup_stale_buckets(max_age_seconds=0.0)
    assert removed == 2
