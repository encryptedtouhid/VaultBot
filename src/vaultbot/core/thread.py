"""Thread ownership and conversation isolation."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ThreadState(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass(slots=True)
class Thread:
    thread_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    owner_id: str = ""
    platform: str = ""
    channel_id: str = ""
    state: ThreadState = ThreadState.ACTIVE
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    participants: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


class ThreadManager:
    """Manages thread ownership and lifecycle."""

    def __init__(self, idle_timeout: float = 3600.0) -> None:
        self._threads: dict[str, Thread] = {}
        self._idle_timeout = idle_timeout

    @property
    def thread_count(self) -> int:
        return len(self._threads)

    def create_thread(self, owner_id: str, platform: str = "", channel_id: str = "") -> Thread:
        thread = Thread(owner_id=owner_id, platform=platform, channel_id=channel_id)
        thread.participants.append(owner_id)
        self._threads[thread.thread_id] = thread
        logger.info("thread_created", thread_id=thread.thread_id, owner=owner_id)
        return thread

    def get_thread(self, thread_id: str) -> Thread | None:
        return self._threads.get(thread_id)

    def is_owner(self, thread_id: str, user_id: str) -> bool:
        thread = self._threads.get(thread_id)
        return thread is not None and thread.owner_id == user_id

    def add_participant(self, thread_id: str, user_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        if user_id not in thread.participants:
            thread.participants.append(user_id)
        return True

    def archive_thread(self, thread_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        thread.state = ThreadState.ARCHIVED
        return True

    def delete_thread(self, thread_id: str) -> bool:
        if thread_id in self._threads:
            self._threads[thread_id].state = ThreadState.DELETED
            del self._threads[thread_id]
            return True
        return False

    def list_user_threads(self, user_id: str) -> list[Thread]:
        return [t for t in self._threads.values() if user_id in t.participants]

    def archive_idle(self) -> int:
        now = time.time()
        count = 0
        for thread in self._threads.values():
            if (
                thread.state == ThreadState.ACTIVE
                and (now - thread.last_activity) > self._idle_timeout
            ):
                thread.state = ThreadState.IDLE
                count += 1
        return count
