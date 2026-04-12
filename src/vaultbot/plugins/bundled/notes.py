"""Built-in notes skill."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class Note:
    note_id: str = ""
    user_id: str = ""
    title: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class NotesSkill:
    """Built-in notes management skill."""

    def __init__(self) -> None:
        self._notes: dict[str, Note] = {}
        self._counter = 0

    @property
    def skill_name(self) -> str:
        return "notes"

    def create(self, user_id: str, title: str, content: str, tags: list[str] | None = None) -> Note:
        self._counter += 1
        nid = f"note_{self._counter}"
        note = Note(note_id=nid, user_id=user_id, title=title, content=content, tags=tags or [])
        self._notes[nid] = note
        return note

    def get(self, note_id: str) -> Note | None:
        return self._notes.get(note_id)

    def update(self, note_id: str, content: str) -> Note | None:
        note = self._notes.get(note_id)
        if note:
            note.content = content
            note.updated_at = time.time()
        return note

    def delete(self, note_id: str) -> bool:
        if note_id in self._notes:
            del self._notes[note_id]
            return True
        return False

    def search(self, user_id: str, query: str) -> list[Note]:
        q = query.lower()
        return [
            n
            for n in self._notes.values()
            if n.user_id == user_id and (q in n.title.lower() or q in n.content.lower())
        ]

    def list_for_user(self, user_id: str) -> list[Note]:
        return [n for n in self._notes.values() if n.user_id == user_id]
