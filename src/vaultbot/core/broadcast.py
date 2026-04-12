"""Multi-channel announcement and broadcast system."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class BroadcastState(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class BroadcastTarget:
    platform: str
    channel_id: str
    sent: bool = False
    error: str = ""


@dataclass(slots=True)
class Broadcast:
    broadcast_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    content: str = ""
    state: BroadcastState = BroadcastState.DRAFT
    targets: list[BroadcastTarget] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    sent_at: float = 0.0


class BroadcastManager:
    """Manages multi-channel announcements."""

    def __init__(self) -> None:
        self._broadcasts: dict[str, Broadcast] = {}

    @property
    def broadcast_count(self) -> int:
        return len(self._broadcasts)

    def create(self, title: str, content: str, targets: list[BroadcastTarget]) -> Broadcast:
        b = Broadcast(title=title, content=content, targets=targets)
        self._broadcasts[b.broadcast_id] = b
        logger.info("broadcast_created", id=b.broadcast_id, targets=len(targets))
        return b

    def get(self, broadcast_id: str) -> Broadcast | None:
        return self._broadcasts.get(broadcast_id)

    async def send(self, broadcast_id: str) -> Broadcast | None:
        b = self._broadcasts.get(broadcast_id)
        if not b or b.state not in (BroadcastState.DRAFT, BroadcastState.SCHEDULED):
            return None
        b.state = BroadcastState.SENDING
        for target in b.targets:
            target.sent = True
        b.state = BroadcastState.COMPLETED
        b.sent_at = time.time()
        logger.info("broadcast_sent", id=broadcast_id)
        return b

    def get_stats(self, broadcast_id: str) -> dict[str, int]:
        b = self._broadcasts.get(broadcast_id)
        if not b:
            return {}
        sent = sum(1 for t in b.targets if t.sent)
        failed = sum(1 for t in b.targets if t.error)
        return {"total": len(b.targets), "sent": sent, "failed": failed}
