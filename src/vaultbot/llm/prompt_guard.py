"""Prompt injection detection and prevention.

Scans both user input and LLM output for known injection patterns.
Provides a wrapper around any LLMProvider to add automatic scanning.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMChunk, LLMProvider, LLMResponse, ToolDefinition
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Known prompt injection patterns (case-insensitive)
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[system\]", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all|your)\s+(you|instructions|rules)", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?(instructions|rules|guidelines)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?(prompt|instructions)", re.IGNORECASE),
    re.compile(r"what\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions)", re.IGNORECASE),
    re.compile(r"repeat\s+(your\s+)?(system\s+)?(prompt|instructions)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+)?(you\s+)?(are|were)\s+", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+)?(are|were)\s+", re.IGNORECASE),
    re.compile(r"from\s+now\s+on\s*,?\s+you", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
]

# Patterns that indicate the LLM output may be compromised
_OUTPUT_LEAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"my\s+system\s+prompt\s+is", re.IGNORECASE),
    re.compile(r"my\s+instructions\s+are", re.IGNORECASE),
    re.compile(r"I\s+(was|am)\s+instructed\s+to", re.IGNORECASE),
]


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Result of scanning text for injection patterns."""

    is_suspicious: bool
    matched_patterns: list[str]
    original_text: str

    @property
    def summary(self) -> str:
        if not self.is_suspicious:
            return "clean"
        return f"suspicious: matched {len(self.matched_patterns)} pattern(s)"


def scan_input(text: str) -> ScanResult:
    """Scan user input for prompt injection patterns."""
    matched = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)

    if matched:
        logger.warning(
            "prompt_injection_detected",
            direction="input",
            pattern_count=len(matched),
        )

    return ScanResult(
        is_suspicious=len(matched) > 0,
        matched_patterns=matched,
        original_text=text,
    )


def scan_output(text: str) -> ScanResult:
    """Scan LLM output for signs of prompt leakage."""
    matched = []
    for pattern in _OUTPUT_LEAK_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)

    if matched:
        logger.warning(
            "prompt_leakage_detected",
            direction="output",
            pattern_count=len(matched),
        )

    return ScanResult(
        is_suspicious=len(matched) > 0,
        matched_patterns=matched,
        original_text=text,
    )


class GuardedLLMProvider:
    """Wraps an LLMProvider with automatic prompt injection scanning.

    Scans user input before sending to the LLM and scans output before
    returning to the user. Suspicious inputs are blocked; suspicious
    outputs are flagged but still returned (with a warning).
    """

    def __init__(
        self,
        provider: LLMProvider,
        *,
        block_suspicious_input: bool = True,
        block_suspicious_output: bool = False,
    ) -> None:
        self._provider = provider
        self._block_input = block_suspicious_input
        self._block_output = block_suspicious_output

    @property
    def provider_name(self) -> str:
        return f"guarded:{self._provider.provider_name}"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        """Complete with injection scanning on input and output."""
        # Scan user messages
        for msg in messages:
            if msg.role == "user":
                result = scan_input(msg.content)
                if result.is_suspicious and self._block_input:
                    return LLMResponse(
                        content="I detected a potential prompt injection attempt "
                        "in your message. This request has been blocked for security.",
                        model="guard",
                        finish_reason="blocked",
                    )

        # Call the underlying provider
        response = await self._provider.complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        )

        # Scan output
        output_result = scan_output(response.content)
        if output_result.is_suspicious and self._block_output:
            return LLMResponse(
                content="The response was blocked due to a potential security issue.",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                finish_reason="blocked",
            )

        return response

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]:
        """Stream with injection scanning on input.

        Note: Output scanning is limited in streaming mode since we can't
        see the full response before chunks are yielded.
        """
        for msg in messages:
            if msg.role == "user":
                result = scan_input(msg.content)
                if result.is_suspicious and self._block_input:
                    yield LLMChunk(
                        content="I detected a potential prompt injection attempt. "
                        "This request has been blocked.",
                        is_final=True,
                    )
                    return

        async for chunk in self._provider.stream(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk
