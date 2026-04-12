"""Thinking/reasoning mode support for advanced LLMs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ThinkingStrategy(str, Enum):
    ALWAYS = "always"
    NEVER = "never"
    AUTO = "auto"


@dataclass(frozen=True, slots=True)
class ThinkingConfig:
    strategy: ThinkingStrategy = ThinkingStrategy.AUTO
    budget_tokens: int = 10000
    show_thinking: bool = False


@dataclass(frozen=True, slots=True)
class ThinkingResult:
    thinking: str = ""
    response: str = ""
    thinking_tokens: int = 0
    response_tokens: int = 0


# Patterns that suggest a complex query needing thinking
_COMPLEXITY_PATTERNS = [
    r"\banalyze\b",
    r"\bcompare\b",
    r"\bexplain\b.*\bwhy\b",
    r"\bstep.by.step\b",
    r"\bdebug\b",
    r"\brefactor\b",
    r"\barchitect\b",
    r"\btrade.?off\b",
    r"\bpros?\s+and\s+cons?\b",
]


def should_use_thinking(query: str, config: ThinkingConfig) -> bool:
    """Determine if thinking mode should be enabled for a query."""
    if config.strategy == ThinkingStrategy.ALWAYS:
        return True
    if config.strategy == ThinkingStrategy.NEVER:
        return False

    # Auto: check for complexity indicators
    if query.strip().lower().startswith("think:"):
        return True

    for pattern in _COMPLEXITY_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return True

    # Long queries are likely complex
    if len(query) > 500:
        return True

    return False


def build_thinking_params(provider: str, config: ThinkingConfig) -> dict[str, object]:
    """Build provider-specific thinking parameters."""
    if provider == "claude":
        return {
            "thinking": {"type": "enabled", "budget_tokens": config.budget_tokens},
        }
    if provider == "openai":
        return {"reasoning_effort": "high"}
    if provider == "deepseek":
        return {"model": "deepseek-reasoner"}
    return {}


def extract_thinking(response_text: str) -> ThinkingResult:
    """Extract thinking from a response that may contain thinking tags."""
    thinking_match = re.search(
        r"<thinking>(.*?)</thinking>",
        response_text,
        re.DOTALL,
    )
    if thinking_match:
        thinking = thinking_match.group(1).strip()
        response = response_text[: thinking_match.start()] + response_text[thinking_match.end() :]
        return ThinkingResult(thinking=thinking, response=response.strip())
    return ThinkingResult(response=response_text)
