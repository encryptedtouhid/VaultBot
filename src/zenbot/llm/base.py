"""Abstract LLM provider protocol.

Any class that implements these methods can serve as an LLM backend —
no inheritance required (structural subtyping via Protocol).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from zenbot.core.message import ChatMessage


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Definition of a tool/function the LLM can call."""

    name: str
    description: str
    parameters: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Response from an LLM completion request."""

    content: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = ""


@dataclass(frozen=True, slots=True)
class LLMChunk:
    """A single chunk from a streaming LLM response."""

    content: str
    is_final: bool = False


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM provider adapters must satisfy."""

    @property
    def provider_name(self) -> str:
        """Unique name identifying this provider (e.g., 'claude', 'openai')."""
        ...

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Generate a completion for the given messages."""
        ...

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        """Stream a completion for the given messages."""
        ...
