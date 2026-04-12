"""Unit tests for process management."""

from __future__ import annotations

from vaultbot.process.command_queue import CommandQueue
from vaultbot.process.executor import ProcessExecutor
from vaultbot.process.supervisor import ProcessState, ProcessSupervisor


class TestProcessExecutor:
    def test_execute_success(self) -> None:
        exe = ProcessExecutor()
        result = exe.execute(["echo", "hello"])
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert exe.execution_count == 1

    def test_execute_failure(self) -> None:
        exe = ProcessExecutor()
        result = exe.execute(["python3", "-c", "raise SystemExit(1)"])
        assert result.exit_code == 1

    def test_execute_timeout(self) -> None:
        exe = ProcessExecutor()
        result = exe.execute(["sleep", "10"], timeout=0.1)
        assert result.timed_out is True

    def test_execute_not_found(self) -> None:
        exe = ProcessExecutor()
        result = exe.execute(["nonexistent_command_xyz"])
        assert result.exit_code == -1


class TestProcessSupervisor:
    def test_register(self) -> None:
        sup = ProcessSupervisor()
        proc = sup.register(["echo", "hi"])
        assert proc.state == ProcessState.PENDING
        assert sup.process_count == 1

    def test_start(self) -> None:
        sup = ProcessSupervisor()
        proc = sup.register(["echo"])
        assert sup.start(proc.process_id) is True
        assert proc.state == ProcessState.RUNNING

    def test_mark_completed(self) -> None:
        sup = ProcessSupervisor()
        proc = sup.register(["echo"])
        sup.start(proc.process_id)
        assert sup.mark_completed(proc.process_id, 0) is True
        assert proc.state == ProcessState.COMPLETED

    def test_mark_failed(self) -> None:
        sup = ProcessSupervisor()
        proc = sup.register(["false"])
        sup.start(proc.process_id)
        assert sup.mark_completed(proc.process_id, 1) is True
        assert proc.state == ProcessState.FAILED

    def test_kill(self) -> None:
        sup = ProcessSupervisor()
        proc = sup.register(["sleep", "100"])
        sup.start(proc.process_id)
        assert sup.kill(proc.process_id) is True
        assert proc.state == ProcessState.KILLED

    def test_list_running(self) -> None:
        sup = ProcessSupervisor()
        p1 = sup.register(["a"])
        sup.register(["b"])
        sup.start(p1.process_id)
        assert len(sup.list_running()) == 1

    def test_cleanup(self) -> None:
        sup = ProcessSupervisor()
        proc = sup.register(["echo"])
        sup.start(proc.process_id)
        sup.mark_completed(proc.process_id)
        cleaned = sup.cleanup_finished()
        assert cleaned == 1
        assert sup.process_count == 0


class TestCommandQueue:
    def test_enqueue_dequeue(self) -> None:
        q = CommandQueue()
        q.enqueue(["echo", "hi"])
        assert q.size == 1
        cmd = q.dequeue()
        assert cmd is not None
        assert cmd.args == ["echo", "hi"]

    def test_priority_ordering(self) -> None:
        q = CommandQueue()
        q.enqueue(["low"], priority=1)
        q.enqueue(["high"], priority=10)
        cmd = q.dequeue()
        assert cmd.args == ["high"]

    def test_dequeue_empty(self) -> None:
        q = CommandQueue()
        assert q.dequeue() is None

    def test_peek(self) -> None:
        q = CommandQueue()
        q.enqueue(["test"])
        assert q.peek() is not None
        assert q.size == 1  # peek doesn't remove

    def test_clear(self) -> None:
        q = CommandQueue()
        q.enqueue(["a"])
        q.enqueue(["b"])
        assert q.clear() == 2
        assert q.is_empty is True

    def test_max_size(self) -> None:
        q = CommandQueue(max_size=2)
        q.enqueue(["a"])
        q.enqueue(["b"])
        q.enqueue(["c"])
        assert q.size == 2
