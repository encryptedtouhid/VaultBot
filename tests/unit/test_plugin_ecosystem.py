"""Unit tests for bundled plugin skills."""

from __future__ import annotations

import time

from vaultbot.plugins.bundled import BUNDLED_SKILLS
from vaultbot.plugins.bundled.notes import NotesSkill
from vaultbot.plugins.bundled.reminder import ReminderSkill
from vaultbot.plugins.bundled.todo import TodoPriority, TodoSkill


class TestBundledSkills:
    def test_bundled_list(self) -> None:
        assert "reminder" in BUNDLED_SKILLS
        assert "notes" in BUNDLED_SKILLS
        assert "todo" in BUNDLED_SKILLS


class TestReminderSkill:
    def test_skill_name(self) -> None:
        assert ReminderSkill().skill_name == "reminder"

    def test_create_and_list(self) -> None:
        s = ReminderSkill()
        r = s.create("u1", "test", time.time() + 3600)
        assert r.reminder_id.startswith("rem_")
        assert len(s.list_for_user("u1")) == 1

    def test_fire_due(self) -> None:
        s = ReminderSkill()
        s.create("u1", "past", time.time() - 10)
        fired = s.fire_due()
        assert len(fired) == 1
        assert fired[0].fired is True

    def test_cancel(self) -> None:
        s = ReminderSkill()
        r = s.create("u1", "test", time.time() + 3600)
        assert s.cancel(r.reminder_id) is True


class TestNotesSkill:
    def test_skill_name(self) -> None:
        assert NotesSkill().skill_name == "notes"

    def test_create_and_get(self) -> None:
        s = NotesSkill()
        n = s.create("u1", "Title", "Content", tags=["work"])
        assert s.get(n.note_id) is not None

    def test_update(self) -> None:
        s = NotesSkill()
        n = s.create("u1", "T", "old")
        s.update(n.note_id, "new")
        assert s.get(n.note_id).content == "new"

    def test_delete(self) -> None:
        s = NotesSkill()
        n = s.create("u1", "T", "C")
        assert s.delete(n.note_id) is True
        assert s.get(n.note_id) is None

    def test_search(self) -> None:
        s = NotesSkill()
        s.create("u1", "Python", "Language notes")
        s.create("u1", "Java", "Other notes")
        assert len(s.search("u1", "python")) == 1


class TestTodoSkill:
    def test_skill_name(self) -> None:
        assert TodoSkill().skill_name == "todo"

    def test_add_and_list(self) -> None:
        s = TodoSkill()
        s.add("u1", "Buy milk")
        assert len(s.list_for_user("u1")) == 1

    def test_complete(self) -> None:
        s = TodoSkill()
        item = s.add("u1", "Task")
        assert s.complete(item.todo_id) is True
        assert len(s.list_for_user("u1")) == 0
        assert len(s.list_for_user("u1", include_done=True)) == 1

    def test_delete(self) -> None:
        s = TodoSkill()
        item = s.add("u1", "Task")
        assert s.delete(item.todo_id) is True

    def test_pending_count(self) -> None:
        s = TodoSkill()
        s.add("u1", "A")
        s.add("u1", "B")
        item = s.add("u1", "C")
        s.complete(item.todo_id)
        assert s.pending_count("u1") == 2

    def test_priority(self) -> None:
        s = TodoSkill()
        item = s.add("u1", "Urgent", priority=TodoPriority.HIGH)
        assert item.priority == TodoPriority.HIGH
