"""Message compaction for long conversations.

When a conversation exceeds the context window budget, older messages
are summarized into a compact form while preserving key information
like names, IDs, and important facts.
"""

from __future__ import annotations

from dataclasses import dataclass

from vaultbot.core.message import ChatMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenBudget:
    """Token budget allocation for context window.

    All values in estimated tokens (1 token ~ 4 chars).
    """
    total: int = 128_000
    system_prompt: int = 2_000
    tools: int = 4_000
    history: int = 100_000
    response: int = 4_000
    compaction_summary: int = 2_000

    @property
    def available_for_history(self) -> int:
        return self.total - self.system_prompt - self.tools - self.response - self.compaction_summary


def estimate_tokens(text: str) -> int:
    """Estimate token count for a string (~4 chars per token)."""
    return max(1, len(text) // 4)


def estimate_messages_tokens(messages: list[ChatMessage]) -> int:
    """Estimate total tokens for a message list."""
    return sum(estimate_tokens(m.content) + 4 for m in messages)  # +4 for role overhead


class ContextCompactor:
    """Compacts conversation history to fit within token budgets.

    When history exceeds the budget, older messages are summarized
    into a single compact message preserving key identifiers and facts.

    Parameters
    ----------
    budget:
        Token budget allocation.
    preserve_recent:
        Number of recent messages to always preserve (not compact).
    """

    def __init__(
        self,
        budget: TokenBudget | None = None,
        preserve_recent: int = 6,
    ) -> None:
        self._budget = budget or TokenBudget()
        self._preserve_recent = preserve_recent
        self._compaction_count: int = 0

    def compact(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        """Compact messages if they exceed the token budget.

        Returns a new message list that fits within the budget. If no
        compaction is needed, returns the original list unchanged.
        """
        total_tokens = estimate_messages_tokens(messages)
        budget = self._budget.available_for_history

        if total_tokens <= budget:
            return messages

        logger.info(
            "context_compaction_needed",
            total_tokens=total_tokens,
            budget=budget,
            message_count=len(messages),
        )

        # Split: system messages, old messages (to compact), recent messages (preserve)
        system_msgs = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]

        preserve_count = min(self._preserve_recent, len(non_system))
        old_msgs = non_system[:-preserve_count] if preserve_count > 0 else non_system
        recent_msgs = non_system[-preserve_count:] if preserve_count > 0 else []

        if not old_msgs:
            return messages  # Nothing to compact

        # Generate summary of old messages
        summary = self._summarize_messages(old_msgs)
        summary_msg = ChatMessage(
            role="system",
            content=f"[Conversation summary of {len(old_msgs)} earlier messages]\n{summary}",
        )

        result = system_msgs + [summary_msg] + recent_msgs
        self._compaction_count += 1

        new_tokens = estimate_messages_tokens(result)
        logger.info(
            "context_compacted",
            original_tokens=total_tokens,
            compacted_tokens=new_tokens,
            messages_removed=len(old_msgs),
            compaction_count=self._compaction_count,
        )

        return result

    @staticmethod
    def _summarize_messages(messages: list[ChatMessage]) -> str:
        """Create a text summary of messages, preserving key identifiers."""
        # Extract unique participants
        participants: set[str] = set()
        topics: list[str] = []
        key_points: list[str] = []

        for msg in messages:
            if msg.role == "user":
                # Extract first few words as topic hints
                words = msg.content.split()[:10]
                if words:
                    topics.append(" ".join(words))
            elif msg.role == "assistant":
                # Keep first sentence of assistant responses
                first_sentence = msg.content.split(".")[0]
                if first_sentence and len(first_sentence) < 200:
                    key_points.append(first_sentence)

        parts: list[str] = []
        if topics:
            unique_topics = list(dict.fromkeys(topics))[:5]  # Dedupe, keep 5
            parts.append(f"Topics discussed: {'; '.join(unique_topics)}")
        if key_points:
            unique_points = list(dict.fromkeys(key_points))[:5]
            parts.append(f"Key points: {'; '.join(unique_points)}")

        parts.append(f"Total messages summarized: {len(messages)}")

        return "\n".join(parts)

    @property
    def compaction_count(self) -> int:
        return self._compaction_count
