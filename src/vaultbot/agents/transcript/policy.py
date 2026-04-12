"""Transcript sanitization policy and tool call ID management."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SanitizeMode(str, Enum):
    FULL = "full"
    IMAGES_ONLY = "images_only"
    NONE = "none"


class ToolCallIdMode(str, Enum):
    PRESERVE = "preserve"
    REGENERATE = "regenerate"
    PROVIDER_SPECIFIC = "provider_specific"


@dataclass(frozen=True, slots=True)
class TranscriptPolicy:
    """Policy for transcript sanitization and handling."""

    sanitize_mode: SanitizeMode = SanitizeMode.FULL
    strip_thinking_blocks: bool = True
    tool_call_id_mode: ToolCallIdMode = ToolCallIdMode.PRESERVE
    max_transcript_turns: int = 100
    preserve_system_prompt: bool = True


@dataclass(frozen=True, slots=True)
class ToolCallMapping:
    """Maps tool call IDs across provider formats."""

    original_id: str
    normalized_id: str
    provider: str


def normalize_tool_call_id(raw_id: str, provider: str = "") -> str:
    """Normalize tool call IDs across providers."""
    if not raw_id:
        import uuid

        return f"call_{uuid.uuid4().hex[:12]}"
    return raw_id


def pair_tool_results(
    messages: list[dict[str, object]],
) -> list[tuple[dict[str, object], dict[str, object] | None]]:
    """Pair tool calls with their results for transcript repair."""
    calls: dict[str, dict[str, object]] = {}
    pairs: list[tuple[dict[str, object], dict[str, object] | None]] = []

    for msg in messages:
        role = msg.get("role", "")
        if role == "assistant" and msg.get("tool_calls"):
            for tc in msg.get("tool_calls", []):  # type: ignore[union-attr]
                tc_id = tc.get("id", "") or tc.get("tool_use_id", "")
                if tc_id:
                    calls[str(tc_id)] = msg
        elif role == "tool":
            tc_id = str(msg.get("tool_call_id", "") or msg.get("tool_use_id", ""))
            call_msg = calls.pop(tc_id, None)
            if call_msg:
                pairs.append((call_msg, msg))

    # Unpaired calls
    for call_msg in calls.values():
        pairs.append((call_msg, None))

    return pairs
