"""Canonical message types that normalize across all messaging platforms."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AttachmentType(str, Enum):
    """Types of message attachments."""

    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"


@dataclass(frozen=True, slots=True)
class Attachment:
    """A file or media attachment on a message."""

    type: AttachmentType
    url: str
    filename: str = ""
    mime_type: str = ""
    size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class InboundMessage:
    """A message received from any messaging platform.

    All platform-specific data is normalized into this canonical form.
    The `raw` field preserves the original platform payload for edge cases.
    """

    id: str
    platform: str
    sender_id: str
    chat_id: str
    text: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    attachments: list[Attachment] = field(default_factory=list)
    reply_to: str | None = None
    raw: Any = field(repr=False, default=None, compare=False)


@dataclass(frozen=True, slots=True)
class OutboundMessage:
    """A message to be sent to a messaging platform."""

    chat_id: str
    text: str
    reply_to: str | None = None
    attachments: list[Attachment] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """A message in the LLM conversation format."""

    role: str  # "system", "user", "assistant"
    content: str
