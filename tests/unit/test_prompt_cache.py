"""Unit tests for prompt caching."""

from __future__ import annotations

from vaultbot.llm.cache import PromptCache


class TestPromptCache:
    def test_put_and_get(self) -> None:
        cache = PromptCache()
        cache.put("hello", "world")
        assert cache.get("hello") == "world"

    def test_get_miss(self) -> None:
        cache = PromptCache()
        assert cache.get("missing") is None

    def test_hit_count(self) -> None:
        cache = PromptCache()
        cache.put("hello", "world")
        cache.get("hello")
        cache.get("hello")
        stats = cache.stats()
        assert stats.hits == 2

    def test_miss_count(self) -> None:
        cache = PromptCache()
        cache.get("missing")
        stats = cache.stats()
        assert stats.misses == 1

    def test_expired_entry(self) -> None:
        cache = PromptCache(default_ttl=0.0)
        cache.put("hello", "world")
        assert cache.get("hello") is None

    def test_invalidate(self) -> None:
        cache = PromptCache()
        cache.put("hello", "world")
        assert cache.invalidate("hello") is True
        assert cache.get("hello") is None

    def test_invalidate_missing(self) -> None:
        cache = PromptCache()
        assert cache.invalidate("nope") is False

    def test_clear(self) -> None:
        cache = PromptCache()
        cache.put("a", "1")
        cache.put("b", "2")
        cache.clear()
        assert cache.stats().total_entries == 0

    def test_eviction(self) -> None:
        cache = PromptCache(max_entries=2)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        assert cache.stats().total_entries == 2

    def test_model_specific_cache(self) -> None:
        cache = PromptCache()
        cache.put("hello", "gpt-reply", model="gpt-4")
        cache.put("hello", "claude-reply", model="claude-3")
        assert cache.get("hello", model="gpt-4") == "gpt-reply"
        assert cache.get("hello", model="claude-3") == "claude-reply"

    def test_hit_rate(self) -> None:
        cache = PromptCache()
        cache.put("hello", "world")
        cache.get("hello")
        cache.get("missing")
        stats = cache.stats()
        assert stats.hit_rate == 0.5
