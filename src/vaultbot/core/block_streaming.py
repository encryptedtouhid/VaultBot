"""Paragraph-aware block streaming with backpressure."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class StreamingMode(str, Enum):
    TOKEN = "token"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class StreamBlock:
    content: str
    is_final: bool = False
    block_type: str = "text"


@dataclass(frozen=True, slots=True)
class BackpressureConfig:
    max_pending_blocks: int = 10
    slow_platform_delay_ms: int = 500
    rate_limit_window_ms: int = 1000


# Sentence boundary pattern
_SENTENCE_END = re.compile(r"[.!?]\s+")
_PARAGRAPH_END = re.compile(r"\n\n+")
_CODE_BLOCK = re.compile(r"```")


class BlockStreamingEngine:
    """Buffer tokens and emit meaningful chunks."""

    def __init__(self, mode: StreamingMode = StreamingMode.SENTENCE) -> None:
        self._mode = mode
        self._buffer = ""
        self._blocks_emitted = 0
        self._in_code_block = False

    @property
    def mode(self) -> StreamingMode:
        return self._mode

    @property
    def blocks_emitted(self) -> int:
        return self._blocks_emitted

    def add_token(self, token: str) -> list[StreamBlock]:
        """Add a token and return any complete blocks."""
        self._buffer += token

        # Track code block state
        if _CODE_BLOCK.search(token):
            self._in_code_block = not self._in_code_block

        # Don't split inside code blocks
        if self._in_code_block:
            return []

        if self._mode == StreamingMode.TOKEN:
            return self._emit(token)

        if self._mode == StreamingMode.SENTENCE:
            return self._emit_on_pattern(_SENTENCE_END)

        if self._mode == StreamingMode.PARAGRAPH:
            return self._emit_on_pattern(_PARAGRAPH_END)

        # FULL mode: buffer everything
        return []

    def flush(self) -> StreamBlock | None:
        """Flush remaining buffer as final block."""
        if self._buffer:
            block = StreamBlock(content=self._buffer, is_final=True)
            self._buffer = ""
            self._blocks_emitted += 1
            return block
        return None

    def reset(self) -> None:
        self._buffer = ""
        self._in_code_block = False

    def _emit(self, content: str) -> list[StreamBlock]:
        block = StreamBlock(content=content)
        self._buffer = ""
        self._blocks_emitted += 1
        return [block]

    def _emit_on_pattern(self, pattern: re.Pattern[str]) -> list[StreamBlock]:
        blocks: list[StreamBlock] = []
        while True:
            match = pattern.search(self._buffer)
            if not match:
                break
            end = match.end()
            block_text = self._buffer[:end]
            self._buffer = self._buffer[end:]
            blocks.append(StreamBlock(content=block_text))
            self._blocks_emitted += 1
        return blocks


class BackpressureManager:
    """Track platform delivery rate and apply backpressure."""

    def __init__(self, config: BackpressureConfig | None = None) -> None:
        self._config = config or BackpressureConfig()
        self._pending = 0
        self._delivered = 0

    @property
    def pending(self) -> int:
        return self._pending

    @property
    def delivered(self) -> int:
        return self._delivered

    def enqueue(self) -> bool:
        """Enqueue a block. Returns False if backpressure should apply."""
        self._pending += 1
        return self._pending <= self._config.max_pending_blocks

    def acknowledge(self) -> None:
        """Acknowledge delivery of a block."""
        if self._pending > 0:
            self._pending -= 1
        self._delivered += 1

    def should_slow_down(self) -> bool:
        return self._pending > self._config.max_pending_blocks // 2
