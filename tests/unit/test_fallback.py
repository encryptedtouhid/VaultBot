"""Unit tests for the model fallback and provider failover system."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMResponse
from vaultbot.llm.fallback import FallbackProvider, ProviderStatus

# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------


class SuccessProvider:
    def __init__(self, name: str = "success") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def complete(self, messages: list[ChatMessage], **kw: object) -> LLMResponse:
        return LLMResponse(
            content=f"from {self._name}", model=self._name, input_tokens=5, output_tokens=3
        )

    async def stream(self, messages: list[ChatMessage], **kw: object) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content=f"stream from {self._name}", is_final=True)


class FailingProvider:
    def __init__(self, name: str = "failing") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def complete(self, messages: list[ChatMessage], **kw: object) -> LLMResponse:
        raise RuntimeError(f"{self._name} is down")

    async def stream(self, messages: list[ChatMessage], **kw: object) -> AsyncIterator[LLMChunk]:
        raise RuntimeError(f"{self._name} stream is down")
        yield  # type: ignore[misc]  # make it a generator


# ---------------------------------------------------------------------------
# ProviderStatus
# ---------------------------------------------------------------------------


class TestProviderStatus:
    def test_initially_available(self) -> None:
        status = ProviderStatus(provider=SuccessProvider())
        assert status.is_available is True

    def test_unavailable_after_failure(self) -> None:
        status = ProviderStatus(provider=SuccessProvider(), cooldown_seconds=60.0)
        status.record_failure()
        assert status.is_available is False

    def test_available_after_cooldown(self) -> None:
        status = ProviderStatus(provider=SuccessProvider(), cooldown_seconds=0.01)
        status.record_failure()
        time.sleep(0.02)
        assert status.is_available is True

    def test_success_resets_failure(self) -> None:
        status = ProviderStatus(provider=SuccessProvider())
        status.record_failure()
        status.record_failure()
        assert status.failure_count == 2

        status.record_success()
        assert status.failure_count == 0
        assert status.last_failure == 0.0
        assert status.success_count == 1

    def test_exponential_backoff(self) -> None:
        status = ProviderStatus(provider=SuccessProvider(), cooldown_seconds=1.0)
        # First failure: 1s cooldown
        status.record_failure()
        assert status.failure_count == 1
        # Second failure: 2s cooldown
        status.record_failure()
        assert status.failure_count == 2


# ---------------------------------------------------------------------------
# FallbackProvider init
# ---------------------------------------------------------------------------


class TestFallbackProviderInit:
    def test_provider_name(self) -> None:
        fb = FallbackProvider([(SuccessProvider(), None)])
        assert fb.provider_name == "fallback"

    def test_requires_at_least_one_provider(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            FallbackProvider([])

    def test_active_provider_is_first(self) -> None:
        fb = FallbackProvider(
            [
                (SuccessProvider("primary"), None),
                (SuccessProvider("secondary"), None),
            ]
        )
        assert fb.active_provider == "primary"

    def test_chain_status(self) -> None:
        fb = FallbackProvider(
            [
                (SuccessProvider("p1"), None),
                (SuccessProvider("p2"), None),
            ]
        )
        status = fb.chain_status
        assert len(status) == 2
        assert status[0]["provider"] == "p1"
        assert status[0]["available"] is True


# ---------------------------------------------------------------------------
# Complete with fallback
# ---------------------------------------------------------------------------


class TestFallbackComplete:
    @pytest.mark.asyncio
    async def test_primary_success(self) -> None:
        fb = FallbackProvider(
            [
                (SuccessProvider("primary"), None),
                (SuccessProvider("backup"), None),
            ]
        )
        result = await fb.complete([ChatMessage(role="user", content="hi")])
        assert "from primary" in result.content

    @pytest.mark.asyncio
    async def test_fallback_to_secondary(self) -> None:
        fb = FallbackProvider(
            [
                (FailingProvider("primary"), None),
                (SuccessProvider("backup"), None),
            ]
        )
        result = await fb.complete([ChatMessage(role="user", content="hi")])
        assert "from backup" in result.content
        assert fb.active_provider == "backup"

    @pytest.mark.asyncio
    async def test_all_fail_raises(self) -> None:
        fb = FallbackProvider(
            [
                (FailingProvider("p1"), None),
                (FailingProvider("p2"), None),
            ]
        )
        with pytest.raises(RuntimeError, match="All providers"):
            await fb.complete([ChatMessage(role="user", content="hi")])

    @pytest.mark.asyncio
    async def test_skips_cooldown_providers(self) -> None:
        fb = FallbackProvider(
            [
                (FailingProvider("primary"), None),
                (SuccessProvider("backup"), None),
            ],
            cooldown_seconds=9999.0,
        )

        # First call: primary fails, falls to backup
        result = await fb.complete([ChatMessage(role="user", content="hi")])
        assert "from backup" in result.content

        # Second call: primary still in cooldown, goes straight to backup
        result = await fb.complete([ChatMessage(role="user", content="hi")])
        assert "from backup" in result.content

    @pytest.mark.asyncio
    async def test_model_override_per_provider(self) -> None:
        provider = SuccessProvider("p1")
        provider.complete = AsyncMock(return_value=LLMResponse(content="ok", model="custom"))
        fb = FallbackProvider([(provider, "custom-model")])

        await fb.complete([ChatMessage(role="user", content="hi")])
        # Verify model was passed
        call_kwargs = provider.complete.call_args
        assert (
            call_kwargs[1].get("model") == "custom-model"
            or call_kwargs.kwargs.get("model") == "custom-model"
        )

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        provider = SuccessProvider("p1")
        fb = FallbackProvider([(provider, None)])

        # Manually set failure
        fb._chain[0].record_failure()
        assert fb._chain[0].failure_count == 1

        # But provider succeeds
        fb._chain[0].last_failure = 0.0  # Clear cooldown for test
        await fb.complete([ChatMessage(role="user", content="hi")])
        assert fb._chain[0].failure_count == 0


# ---------------------------------------------------------------------------
# Stream with fallback
# ---------------------------------------------------------------------------


class TestFallbackStream:
    @pytest.mark.asyncio
    async def test_stream_primary_success(self) -> None:
        fb = FallbackProvider(
            [
                (SuccessProvider("primary"), None),
                (SuccessProvider("backup"), None),
            ]
        )
        chunks = []
        async for chunk in fb.stream([ChatMessage(role="user", content="hi")]):
            chunks.append(chunk)
        assert any("stream from primary" in c.content for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_fallback(self) -> None:
        fb = FallbackProvider(
            [
                (FailingProvider("primary"), None),
                (SuccessProvider("backup"), None),
            ]
        )
        chunks = []
        async for chunk in fb.stream([ChatMessage(role="user", content="hi")]):
            chunks.append(chunk)
        assert any("stream from backup" in c.content for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_all_fail(self) -> None:
        fb = FallbackProvider(
            [
                (FailingProvider("p1"), None),
                (FailingProvider("p2"), None),
            ]
        )
        with pytest.raises(RuntimeError, match="All providers"):
            async for _ in fb.stream([ChatMessage(role="user", content="hi")]):
                pass


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestFallbackReset:
    def test_reset_clears_all(self) -> None:
        fb = FallbackProvider(
            [
                (SuccessProvider("p1"), None),
                (SuccessProvider("p2"), None),
            ]
        )
        fb._chain[0].record_failure()
        fb._chain[1].record_success()

        fb.reset_all()

        for s in fb._chain:
            assert s.failure_count == 0
            assert s.success_count == 0
            assert s.last_failure == 0.0
