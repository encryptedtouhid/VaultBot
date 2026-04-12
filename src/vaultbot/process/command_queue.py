"""Command queueing and scheduling."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class QueuedCommand:
    command_id: str = ""
    args: list[str] = field(default_factory=list)
    priority: int = 0
    queued_at: float = field(default_factory=time.time)
    timeout: float = 30.0


class CommandQueue:
    """Priority-based command queue."""

    def __init__(self, max_size: int = 100) -> None:
        self._queue: list[QueuedCommand] = []
        self._max_size = max_size
        self._counter = 0

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def enqueue(self, args: list[str], priority: int = 0, timeout: float = 30.0) -> QueuedCommand:
        self._counter += 1
        cmd = QueuedCommand(
            command_id=f"cmd_{self._counter}",
            args=args,
            priority=priority,
            timeout=timeout,
        )
        self._queue.append(cmd)
        self._queue.sort(key=lambda c: c.priority, reverse=True)
        if len(self._queue) > self._max_size:
            self._queue.pop()
        return cmd

    def dequeue(self) -> QueuedCommand | None:
        if self._queue:
            return self._queue.pop(0)
        return None

    def peek(self) -> QueuedCommand | None:
        return self._queue[0] if self._queue else None

    def clear(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        return count
