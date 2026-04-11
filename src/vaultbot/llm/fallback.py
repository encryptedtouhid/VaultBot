"""Model fallback and provider failover system.

Wraps multiple LLM providers in a priority chain.  If the primary provider
fails (rate limit, timeout, 5xx, network error), the system automatically
falls over to the next provider in the chain.

Each provider has an associated cooldown: after a failure, the provider is
temporarily removed from rotation and re-tried after the cooldown expires.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMResponse, LLMProvider, ToolDefinition
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProviderStatus:
    """Tracks the health status of a provider in the fallback chain."""

    provider: LLMProvider
    model: str | None = None
    cooldown_seconds: float = 60.0
    last_failure: float = 0.0
    failure_count: int = 0
    success_count: int = 0

    @property
    def is_available(self) -> bool:
        """Return True if the provider is not in cooldown."""
        if self.last_failure == 0.0:
            return True
        elapsed = time.monotonic() - self.last_failure
        # Exponential backoff capped at 5 min
        backoff = min(self.cooldown_seconds * (2 ** min(self.failure_count - 1, 4)), 300.0)
        return elapsed >= backoff

    def record_failure(self) -> None:
        """Record a provider failure."""
        self.failure_count += 1
        self.last_failure = time.monotonic()

    def record_success(self) -> None:
        """Record a provider success, resetting failure tracking."""
        self.success_count += 1
        self.failure_count = 0
        self.last_failure = 0.0


class FallbackProvider:
    """LLM provider with automatic failover across a chain of providers.

    Parameters
    ----------
    providers:
        List of ``(provider, optional_model_override)`` tuples in
        priority order.  The first available provider is tried first.
    cooldown_seconds:
        Default cooldown after a provider failure before retrying it.
    """

    def __init__(
        self,
        providers: list[tuple[LLMProvider, str | None]],
        cooldown_seconds: float = 60.0,
    ) -> None:
        if not providers:
            raise ValueError("FallbackProvider requires at least one provider")

        self._chain: list[ProviderStatus] = [
            ProviderStatus(
                provider=p,
                model=m,
                cooldown_seconds=cooldown_seconds,
            )
            for p, m in providers
        ]
        self._last_used: ProviderStatus | None = None

    @property
    def provider_name(self) -> str:
        return "fallback"

    @property
    def active_provider(self) -> str:
        """Name of the currently active (last used or first available) provider."""
        if self._last_used:
            return self._last_used.provider.provider_name
        for status in self._chain:
            if status.is_available:
                return status.provider.provider_name
        return self._chain[0].provider.provider_name

    @property
    def chain_status(self) -> list[dict[str, object]]:
        """Return the current status of all providers in the chain."""
        return [
            {
                "provider": s.provider.provider_name,
                "available": s.is_available,
                "failures": s.failure_count,
                "successes": s.success_count,
            }
            for s in self._chain
        ]

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Try each provider in order until one succeeds."""
        last_error: Exception | None = None

        for status in self._chain:
            if not status.is_available:
                logger.debug(
                    "fallback_provider_in_cooldown",
                    provider=status.provider.provider_name,
                    failures=status.failure_count,
                )
                continue

            try:
                result = await status.provider.complete(
                    messages,
                    model=model or status.model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                )
                status.record_success()
                self._last_used = status
                return result
            except Exception as exc:
                status.record_failure()
                last_error = exc
                logger.warning(
                    "fallback_provider_failed",
                    provider=status.provider.provider_name,
                    error=str(exc),
                    failures=status.failure_count,
                )
                continue

        raise RuntimeError(
            f"All providers in fallback chain failed. Last error: {last_error}"
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        """Stream from the first available provider, falling back on error."""
        last_error: Exception | None = None

        for status in self._chain:
            if not status.is_available:
                continue

            try:
                async for chunk in status.provider.stream(
                    messages,
                    model=model or status.model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield chunk
                status.record_success()
                self._last_used = status
                return
            except Exception as exc:
                status.record_failure()
                last_error = exc
                logger.warning(
                    "fallback_stream_failed",
                    provider=status.provider.provider_name,
                    error=str(exc),
                )
                continue

        raise RuntimeError(
            f"All providers in fallback chain failed to stream. Last error: {last_error}"
        )

    def reset_all(self) -> None:
        """Reset all provider statuses (clear cooldowns and counters)."""
        for status in self._chain:
            status.failure_count = 0
            status.success_count = 0
            status.last_failure = 0.0
        self._last_used = None
