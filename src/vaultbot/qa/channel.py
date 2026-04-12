"""QA channel for testing bot responses without real platforms."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class QAMessage:
    role: str = "user"
    content: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass(slots=True)
class QAConversation:
    conversation_id: str = ""
    messages: list[QAMessage] = field(default_factory=list)


class QAChannel:
    """In-memory QA channel for testing bot responses."""

    def __init__(self) -> None:
        self._conversations: dict[str, QAConversation] = {}
        self._counter = 0

    @property
    def conversation_count(self) -> int:
        return len(self._conversations)

    def create_conversation(self) -> QAConversation:
        self._counter += 1
        cid = f"qa_{self._counter}"
        conv = QAConversation(conversation_id=cid)
        self._conversations[cid] = conv
        return conv

    def send_message(self, conversation_id: str, content: str) -> QAMessage | None:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return None
        msg = QAMessage(role="user", content=content)
        conv.messages.append(msg)
        return msg

    def add_response(self, conversation_id: str, content: str) -> QAMessage | None:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return None
        msg = QAMessage(role="assistant", content=content)
        conv.messages.append(msg)
        return msg

    def get_history(self, conversation_id: str) -> list[QAMessage]:
        conv = self._conversations.get(conversation_id)
        return conv.messages if conv else []

    def clear_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            self._conversations[conversation_id].messages.clear()
            return True
        return False
