"""Built-in todo skill."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class TodoPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(slots=True)
class TodoItem:
    todo_id: str = ""
    user_id: str = ""
    title: str = ""
    done: bool = False
    priority: TodoPriority = TodoPriority.MEDIUM
    created_at: float = field(default_factory=time.time)


class TodoSkill:
    """Built-in todo list management skill."""

    def __init__(self) -> None:
        self._items: dict[str, TodoItem] = {}
        self._counter = 0

    @property
    def skill_name(self) -> str:
        return "todo"

    def add(
        self, user_id: str, title: str, priority: TodoPriority = TodoPriority.MEDIUM
    ) -> TodoItem:
        self._counter += 1
        tid = f"todo_{self._counter}"
        item = TodoItem(todo_id=tid, user_id=user_id, title=title, priority=priority)
        self._items[tid] = item
        return item

    def complete(self, todo_id: str) -> bool:
        item = self._items.get(todo_id)
        if item:
            item.done = True
            return True
        return False

    def delete(self, todo_id: str) -> bool:
        if todo_id in self._items:
            del self._items[todo_id]
            return True
        return False

    def list_for_user(self, user_id: str, include_done: bool = False) -> list[TodoItem]:
        return [
            i for i in self._items.values() if i.user_id == user_id and (include_done or not i.done)
        ]

    def pending_count(self, user_id: str) -> int:
        return len([i for i in self._items.values() if i.user_id == user_id and not i.done])
