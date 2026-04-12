"""Unit tests for advanced media understanding."""

from __future__ import annotations

import pytest

from vaultbot.media.attachment_cache import AttachmentCache
from vaultbot.media.vision import VisionEngine, VisionProvider, VisionRequest, VisionResult


class MockVisionProvider:
    def __init__(self, name: str = "mock_vision") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def analyze(self, request: VisionRequest) -> VisionResult:
        return VisionResult(description="A test image", provider=self._name)


class FailingVisionProvider:
    @property
    def provider_name(self) -> str:
        return "failing"

    async def analyze(self, request: VisionRequest) -> VisionResult:
        raise RuntimeError("Provider failed")


class TestVisionEngine:
    def test_mock_is_provider(self) -> None:
        assert isinstance(MockVisionProvider(), VisionProvider)

    @pytest.mark.asyncio
    async def test_analyze(self) -> None:
        engine = VisionEngine()
        engine.register(MockVisionProvider())
        result = await engine.analyze(VisionRequest(question="What is this?"))
        assert result.description == "A test image"
        assert engine.analysis_count == 1

    @pytest.mark.asyncio
    async def test_analyze_specific_provider(self) -> None:
        engine = VisionEngine()
        engine.register(MockVisionProvider("a"))
        engine.register(MockVisionProvider("b"))
        result = await engine.analyze(VisionRequest(), provider="b")
        assert result.provider == "b"

    @pytest.mark.asyncio
    async def test_fallback(self) -> None:
        engine = VisionEngine()
        engine.register(FailingVisionProvider())
        engine.register(MockVisionProvider("backup"))
        result = await engine.analyze(VisionRequest())
        assert result.provider == "backup"

    @pytest.mark.asyncio
    async def test_all_fail(self) -> None:
        engine = VisionEngine()
        engine.register(FailingVisionProvider())
        with pytest.raises(RuntimeError, match="All vision providers failed"):
            await engine.analyze(VisionRequest())


class TestAttachmentCache:
    def test_put_and_get(self) -> None:
        cache = AttachmentCache()
        cache.put("http://img.com/a.jpg", b"data", "image/jpeg")
        entry = cache.get("http://img.com/a.jpg")
        assert entry is not None
        assert entry.data == b"data"

    def test_get_miss(self) -> None:
        cache = AttachmentCache()
        assert cache.get("http://nope.com") is None

    def test_ttl_expiry(self) -> None:
        cache = AttachmentCache(ttl_seconds=0)
        cache.put("http://img.com/a.jpg", b"data")
        assert cache.get("http://img.com/a.jpg") is None

    def test_invalidate(self) -> None:
        cache = AttachmentCache()
        cache.put("http://img.com/a.jpg", b"data")
        assert cache.invalidate("http://img.com/a.jpg") is True
        assert cache.size == 0

    def test_eviction(self) -> None:
        cache = AttachmentCache(max_entries=2)
        cache.put("http://a.com", b"1")
        cache.put("http://b.com", b"2")
        cache.put("http://c.com", b"3")
        assert cache.size == 2

    def test_clear(self) -> None:
        cache = AttachmentCache()
        cache.put("http://a.com", b"1")
        cache.clear()
        assert cache.size == 0
