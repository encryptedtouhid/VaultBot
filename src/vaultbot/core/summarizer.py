"""LLM-powered conversation summarization.

When conversation history grows beyond the context window, the summarizer
compresses older messages into a concise summary. This preserves context
while keeping token usage manageable.
"""

from __future__ import annotations

from vaultbot.core.message import ChatMessage
from vaultbot.llm.base import LLMProvider
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_SUMMARY_SYSTEM_PROMPT = (
    "You are a conversation summarizer. Summarize the following conversation "
    "in 2-3 concise sentences. Preserve key facts, decisions, and user "
    "preferences. Do not include greetings or filler."
)


class ConversationSummarizer:
    """Summarizes conversation history using an LLM."""

    def __init__(
        self,
        llm: LLMProvider,
        *,
        summary_threshold: int = 30,
        keep_recent: int = 10,
    ) -> None:
        self._llm = llm
        self._summary_threshold = summary_threshold
        self._keep_recent = keep_recent

    async def should_summarize(self, message_count: int) -> bool:
        """Check if the conversation should be summarized."""
        return message_count >= self._summary_threshold

    async def summarize(
        self,
        messages: list[ChatMessage],
        existing_summary: str = "",
    ) -> str:
        """Summarize older messages, keeping recent ones intact.

        Args:
            messages: Full conversation history.
            existing_summary: Previous summary to build upon.

        Returns:
            A concise summary of the conversation so far.
        """
        if len(messages) <= self._keep_recent:
            return existing_summary

        # Split into old (to summarize) and recent (to keep)
        old_messages = messages[: -self._keep_recent]

        # Build the summarization prompt
        conversation_text = self._format_messages(old_messages)

        prompt_parts = []
        if existing_summary:
            prompt_parts.append(f"Previous summary:\n{existing_summary}\n")
        prompt_parts.append(f"New conversation to incorporate:\n{conversation_text}")

        summary_messages = [
            ChatMessage(role="system", content=_SUMMARY_SYSTEM_PROMPT),
            ChatMessage(role="user", content="\n".join(prompt_parts)),
        ]

        response = await self._llm.complete(
            summary_messages,
            temperature=0.3,
            max_tokens=500,
        )

        logger.info(
            "conversation_summarized",
            old_message_count=len(old_messages),
            summary_length=len(response.content),
        )

        return response.content

    @staticmethod
    def _format_messages(messages: list[ChatMessage]) -> str:
        """Format messages into readable text for the summarizer."""
        lines = []
        for msg in messages:
            if msg.role == "system":
                continue
            role = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    def get_context_with_summary(
        self,
        summary: str,
        recent_messages: list[ChatMessage],
        system_prompt: str = "",
    ) -> list[ChatMessage]:
        """Build a message list with summary + recent messages.

        This replaces old messages with a summary to stay within
        token limits while preserving context.
        """
        messages: list[ChatMessage] = []

        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))

        if summary:
            messages.append(
                ChatMessage(
                    role="system",
                    content=f"Previous conversation summary:\n{summary}",
                )
            )

        messages.extend(recent_messages)
        return messages
