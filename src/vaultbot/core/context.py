"""Conversation context management with sliding window."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.core.message import ChatMessage


@dataclass
class ConversationContext:
    """Manages conversation history for a single chat with a sliding window."""

    chat_id: str
    system_prompt: str = ""
    max_history: int = 20
    _messages: list[ChatMessage] = field(default_factory=list)

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the conversation history."""
        self._messages.append(message)
        # Trim to sliding window, keeping system prompt space
        if len(self._messages) > self.max_history:
            self._messages = self._messages[-self.max_history :]

    def get_messages(self) -> list[ChatMessage]:
        """Get the full message list for LLM input, including system prompt."""
        messages: list[ChatMessage] = []
        if self.system_prompt:
            messages.append(ChatMessage(role="system", content=self.system_prompt))
        messages.extend(self._messages)
        return messages

    def clear(self) -> None:
        """Clear the conversation history."""
        self._messages.clear()

    @property
    def message_count(self) -> int:
        return len(self._messages)


class ContextManager:
    """Manages conversation contexts across multiple chats."""

    def __init__(self, system_prompt: str = "", max_history: int = 20) -> None:
        self._system_prompt = system_prompt
        self._max_history = max_history
        self._contexts: dict[str, ConversationContext] = {}

    def get(self, chat_id: str) -> ConversationContext:
        """Get or create a conversation context for a chat."""
        if chat_id not in self._contexts:
            self._contexts[chat_id] = ConversationContext(
                chat_id=chat_id,
                system_prompt=self._system_prompt,
                max_history=self._max_history,
            )
        return self._contexts[chat_id]

    def clear(self, chat_id: str) -> None:
        """Clear the context for a specific chat."""
        if chat_id in self._contexts:
            self._contexts[chat_id].clear()

    def clear_all(self) -> None:
        """Clear all conversation contexts."""
        self._contexts.clear()
