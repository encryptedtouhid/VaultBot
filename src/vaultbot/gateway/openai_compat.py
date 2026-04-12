"""OpenAI-compatible /v1/chat/completions endpoint."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class OpenAIRequest:
    """OpenAI-format chat completion request."""

    model: str = ""
    messages: list[dict[str, str]] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    tools: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OpenAIChoice:
    index: int = 0
    message: dict[str, str] = field(default_factory=dict)
    finish_reason: str = "stop"


@dataclass(frozen=True, slots=True)
class OpenAIUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class OpenAIResponse:
    """OpenAI-format chat completion response."""

    id: str = ""
    model: str = ""
    choices: list[OpenAIChoice] = field(default_factory=list)
    usage: OpenAIUsage = field(default_factory=OpenAIUsage)
    object: str = "chat.completion"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "object": self.object,
            "model": self.model,
            "choices": [
                {
                    "index": c.index,
                    "message": c.message,
                    "finish_reason": c.finish_reason,
                }
                for c in self.choices
            ],
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens,
            },
        }


# Model name mapping: OpenAI names -> VaultBot provider names
_MODEL_MAP: dict[str, tuple[str, str]] = {
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "gpt-4-turbo": ("openai", "gpt-4-turbo"),
    "claude-sonnet-4-20250514": ("claude", "claude-sonnet-4-20250514"),
    "claude-opus-4-20250514": ("claude", "claude-opus-4-20250514"),
}


def resolve_model(model_name: str) -> tuple[str, str]:
    """Resolve an OpenAI model name to (provider, model) tuple."""
    if model_name in _MODEL_MAP:
        return _MODEL_MAP[model_name]
    # Default: treat as compatible provider
    return ("compatible", model_name)


def format_sse_chunk(chunk_id: str, model: str, content: str, finish: bool = False) -> str:
    """Format a streaming SSE chunk."""
    if finish:
        return 'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
    return (
        f'data: {{"id":"{chunk_id}","model":"{model}",'
        f'"choices":[{{"delta":{{"content":"{content}"}}}}]}}\n\n'
    )
