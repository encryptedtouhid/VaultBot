"""E2E integration tests for the fallback provider system."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMResponse
from vaultbot.llm.fallback import FallbackProvider


class PrimaryProvider:
    """Simulates a provider that fails N times then recovers."""

    def __init__(self, fail_count: int = 2) -> None:
        self._fail_count = fail_count
        self._calls = 0

    @property
    def provider_name(self) -> str:
        return "primary"

    async def complete(self, messages: list[ChatMessage], **kw: object) -> LLMResponse:
        self._calls += 1
        if self._calls <= self._fail_count:
            raise RuntimeError("primary temporarily down")
        return LLMResponse(content="primary recovered", model="primary")

    async def stream(self, messages: list[ChatMessage], **kw: object) -> AsyncIterator[LLMChunk]:
        self._calls += 1
        if self._calls <= self._fail_count:
            raise RuntimeError("primary stream down")
        yield LLMChunk(content="primary stream recovered", is_final=True)


class BackupProvider:
    @property
    def provider_name(self) -> str:
        return "backup"

    async def complete(self, messages: list[ChatMessage], **kw: object) -> LLMResponse:
        return LLMResponse(content="backup response", model="backup")

    async def stream(self, messages: list[ChatMessage], **kw: object) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content="backup stream", is_final=True)


class TestE2EFallbackScenarios:
    @pytest.mark.asyncio
    async def test_graceful_degradation_and_recovery(self) -> None:
        """Primary fails, backup handles it, primary recovers later."""
        primary = PrimaryProvider(fail_count=1)
        backup = BackupProvider()

        fb = FallbackProvider(
            [
                (primary, None),
                (backup, None),
            ],
            cooldown_seconds=0.01,
        )  # Very short cooldown for test

        # First call: primary fails, backup responds
        result = await fb.complete([ChatMessage(role="user", content="hi")])
        assert result.content == "backup response"

        # Wait for cooldown
        import time

        time.sleep(0.02)

        # Second call: primary should recover
        result = await fb.complete([ChatMessage(role="user", content="hi")])
        assert result.content == "primary recovered"

    @pytest.mark.asyncio
    async def test_chain_status_reflects_failures(self) -> None:
        """Chain status should show failure counts."""
        primary = PrimaryProvider(fail_count=99)
        backup = BackupProvider()

        fb = FallbackProvider([(primary, None), (backup, None)])

        await fb.complete([ChatMessage(role="user", content="hi")])

        status = fb.chain_status
        assert status[0]["failures"] == 1
        assert status[1]["successes"] == 1

    @pytest.mark.asyncio
    async def test_three_provider_chain(self) -> None:
        """Three providers: first two fail, third succeeds."""
        fb = FallbackProvider(
            [
                (PrimaryProvider(fail_count=99), None),
                (PrimaryProvider(fail_count=99), None),
                (BackupProvider(), None),
            ]
        )

        result = await fb.complete([ChatMessage(role="user", content="hi")])
        assert result.content == "backup response"

        status = fb.chain_status
        assert status[0]["failures"] == 1
        assert status[1]["failures"] == 1
        assert status[2]["successes"] == 1

    @pytest.mark.asyncio
    async def test_stream_fallback_e2e(self) -> None:
        """Stream: primary fails, backup streams."""
        fb = FallbackProvider(
            [
                (PrimaryProvider(fail_count=99), None),
                (BackupProvider(), None),
            ]
        )

        chunks = []
        async for chunk in fb.stream([ChatMessage(role="user", content="hi")]):
            chunks.append(chunk)

        assert any("backup" in c.content for c in chunks)

    @pytest.mark.asyncio
    async def test_reset_allows_retry(self) -> None:
        """After reset, all providers are retried from scratch."""
        primary = PrimaryProvider(fail_count=1)
        backup = BackupProvider()

        fb = FallbackProvider([(primary, None), (backup, None)], cooldown_seconds=9999)

        # First: primary fails
        await fb.complete([ChatMessage(role="user", content="hi")])

        # Primary is in cooldown, reset
        fb.reset_all()

        # Now primary should be available again (and succeed since fail_count was 1)
        result = await fb.complete([ChatMessage(role="user", content="hi")])
        assert result.content == "primary recovered"
