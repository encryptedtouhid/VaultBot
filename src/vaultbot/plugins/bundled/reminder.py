"""Built-in reminder skill."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class Reminder:
    reminder_id: str = ""
    user_id: str = ""
    message: str = ""
    due_at: float = 0.0
    created_at: float = field(default_factory=time.time)
    fired: bool = False


class ReminderSkill:
    """Built-in reminder management skill."""

    def __init__(self) -> None:
        self._reminders: dict[str, Reminder] = {}
        self._counter = 0

    @property
    def skill_name(self) -> str:
        return "reminder"

    def create(self, user_id: str, message: str, due_at: float) -> Reminder:
        self._counter += 1
        rid = f"rem_{self._counter}"
        r = Reminder(reminder_id=rid, user_id=user_id, message=message, due_at=due_at)
        self._reminders[rid] = r
        return r

    def list_for_user(self, user_id: str) -> list[Reminder]:
        return [r for r in self._reminders.values() if r.user_id == user_id and not r.fired]

    def fire_due(self) -> list[Reminder]:
        now = time.time()
        fired = []
        for r in self._reminders.values():
            if not r.fired and r.due_at <= now:
                r.fired = True
                fired.append(r)
        return fired

    def cancel(self, reminder_id: str) -> bool:
        if reminder_id in self._reminders:
            del self._reminders[reminder_id]
            return True
        return False
