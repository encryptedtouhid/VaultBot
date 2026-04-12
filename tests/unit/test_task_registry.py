"""Unit tests for task registry."""

from __future__ import annotations

from vaultbot.core.task_registry import TaskRegistry, TaskStatus


class TestTaskRegistry:
    def test_create(self) -> None:
        reg = TaskRegistry()
        task = reg.create("test_task", owner_id="u1")
        assert task.status == TaskStatus.PENDING
        assert reg.count == 1

    def test_start(self) -> None:
        reg = TaskRegistry()
        task = reg.create("test")
        assert reg.start(task.task_id) is True
        assert task.status == TaskStatus.RUNNING

    def test_complete(self) -> None:
        reg = TaskRegistry()
        task = reg.create("test")
        reg.start(task.task_id)
        assert reg.complete(task.task_id, "done") is True
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 1.0

    def test_fail(self) -> None:
        reg = TaskRegistry()
        task = reg.create("test")
        reg.start(task.task_id)
        assert reg.fail(task.task_id, "error") is True
        assert task.status == TaskStatus.FAILED

    def test_cancel(self) -> None:
        reg = TaskRegistry()
        task = reg.create("test")
        assert reg.cancel(task.task_id) is True
        assert task.status == TaskStatus.CANCELLED

    def test_list_by_owner(self) -> None:
        reg = TaskRegistry()
        reg.create("a", owner_id="u1")
        reg.create("b", owner_id="u2")
        reg.create("c", owner_id="u1")
        assert len(reg.list_by_owner("u1")) == 2

    def test_list_by_status(self) -> None:
        reg = TaskRegistry()
        t1 = reg.create("a")
        reg.create("b")
        reg.start(t1.task_id)
        assert len(reg.list_by_status(TaskStatus.RUNNING)) == 1

    def test_delete(self) -> None:
        reg = TaskRegistry()
        task = reg.create("test")
        assert reg.delete(task.task_id) is True
        assert reg.count == 0

    def test_cleanup_old(self) -> None:
        reg = TaskRegistry()
        task = reg.create("old")
        reg.start(task.task_id)
        reg.complete(task.task_id)
        task.finished_at = 1.0  # Make it very old
        cleaned = reg.cleanup_old(max_age_seconds=0)
        assert cleaned == 1
