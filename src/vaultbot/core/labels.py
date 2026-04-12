"""Conversation labels, naming, and rich output directives."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class ConversationLabel:
    name: str
    color: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class ConversationMeta:
    conversation_id: str
    name: str = ""
    labels: list[ConversationLabel] = field(default_factory=list)
    auto_name: str = ""


class LabelManager:
    """Manages conversation labels and naming."""

    def __init__(self) -> None:
        self._conversations: dict[str, ConversationMeta] = {}

    def get_or_create(self, conversation_id: str) -> ConversationMeta:
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationMeta(conversation_id=conversation_id)
        return self._conversations[conversation_id]

    def set_name(self, conversation_id: str, name: str) -> None:
        meta = self.get_or_create(conversation_id)
        meta.name = name
        logger.info("conversation_named", id=conversation_id, name=name)

    def add_label(self, conversation_id: str, label_name: str, color: str = "") -> None:
        meta = self.get_or_create(conversation_id)
        if not any(lbl.name == label_name for lbl in meta.labels):
            meta.labels.append(ConversationLabel(name=label_name, color=color))

    def remove_label(self, conversation_id: str, label_name: str) -> bool:
        meta = self._conversations.get(conversation_id)
        if not meta:
            return False
        before = len(meta.labels)
        meta.labels = [lbl for lbl in meta.labels if lbl.name != label_name]
        return len(meta.labels) < before

    def get_labels(self, conversation_id: str) -> list[ConversationLabel]:
        meta = self._conversations.get(conversation_id)
        return list(meta.labels) if meta else []

    def search_by_label(self, label_name: str) -> list[str]:
        return [
            cid
            for cid, meta in self._conversations.items()
            if any(lbl.name == label_name for lbl in meta.labels)
        ]

    def auto_name(self, conversation_id: str, first_message: str) -> str:
        """Generate an automatic name from the first message."""
        name = first_message[:50].strip()
        if len(first_message) > 50:
            name += "..."
        meta = self.get_or_create(conversation_id)
        meta.auto_name = name
        return name
