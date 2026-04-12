"""Reply pipeline orchestration with streaming and media staging."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ReplyState(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


@dataclass(slots=True)
class ReplyContext:
    session_id: str = ""
    model: str = ""
    state: ReplyState = ReplyState.IDLE
    started_at: float = 0.0
    finished_at: float = 0.0
    input_text: str = ""
    output_text: str = ""
    media_paths: list[str] = field(default_factory=list)
    error: str = ""


class ReplyPipeline:
    """Orchestrates the reply lifecycle with streaming and abort support."""

    def __init__(self) -> None:
        self._active_replies: dict[str, ReplyContext] = {}

    @property
    def active_count(self) -> int:
        return len(self._active_replies)

    def start_reply(self, session_id: str, input_text: str, model: str = "") -> ReplyContext:
        ctx = ReplyContext(
            session_id=session_id,
            model=model,
            state=ReplyState.PROCESSING,
            started_at=time.time(),
            input_text=input_text,
        )
        self._active_replies[session_id] = ctx
        logger.info("reply_started", session_id=session_id)
        return ctx

    def stream_chunk(self, session_id: str, chunk: str) -> bool:
        ctx = self._active_replies.get(session_id)
        if not ctx or ctx.state == ReplyState.ABORTED:
            return False
        ctx.state = ReplyState.STREAMING
        ctx.output_text += chunk
        return True

    def complete_reply(self, session_id: str) -> ReplyContext | None:
        ctx = self._active_replies.pop(session_id, None)
        if not ctx:
            return None
        ctx.state = ReplyState.COMPLETED
        ctx.finished_at = time.time()
        logger.info(
            "reply_completed",
            session_id=session_id,
            duration_ms=int((ctx.finished_at - ctx.started_at) * 1000),
        )
        return ctx

    def abort_reply(self, session_id: str) -> bool:
        ctx = self._active_replies.get(session_id)
        if not ctx:
            return False
        ctx.state = ReplyState.ABORTED
        ctx.finished_at = time.time()
        self._active_replies.pop(session_id, None)
        return True

    def fail_reply(self, session_id: str, error: str) -> bool:
        ctx = self._active_replies.get(session_id)
        if not ctx:
            return False
        ctx.state = ReplyState.FAILED
        ctx.error = error
        ctx.finished_at = time.time()
        self._active_replies.pop(session_id, None)
        return True

    def get_active(self, session_id: str) -> ReplyContext | None:
        return self._active_replies.get(session_id)
