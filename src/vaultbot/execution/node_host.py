"""Node host for system command execution with approval.

NOTE: This module manages approval workflows for command execution.
It does NOT directly execute commands — it evaluates policies and manages
the approval queue. Actual execution is delegated to ProcessExecutor
which uses argument lists (no shell) to prevent injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(slots=True)
class ExecRequest:
    command: list[str]
    approval: ApprovalState = ApprovalState.PENDING
    requester: str = ""
    reason: str = ""


class ExecPolicy:
    """Policy engine for command execution approval."""

    def __init__(self) -> None:
        self._allowed_commands: set[str] = {"echo", "ls", "cat", "python3", "git"}
        self._denied_commands: set[str] = {"rm", "dd", "mkfs", "shutdown"}

    def evaluate(self, command: list[str]) -> ApprovalState:
        if not command:
            return ApprovalState.DENIED
        binary = command[0].split("/")[-1]
        if binary in self._denied_commands:
            return ApprovalState.DENIED
        if binary in self._allowed_commands:
            return ApprovalState.APPROVED
        return ApprovalState.PENDING

    def add_allowed(self, command: str) -> None:
        self._allowed_commands.add(command)

    def add_denied(self, command: str) -> None:
        self._denied_commands.add(command)


class NodeHost:
    """Manages command approval workflow (not execution)."""

    def __init__(self, policy: ExecPolicy | None = None) -> None:
        self._policy = policy or ExecPolicy()
        self._pending: list[ExecRequest] = []
        self._approved_count = 0

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def approved_count(self) -> int:
        return self._approved_count

    def request(self, command: list[str], requester: str = "") -> ExecRequest:
        req = ExecRequest(command=command, requester=requester)
        req.approval = self._policy.evaluate(command)
        if req.approval == ApprovalState.PENDING:
            self._pending.append(req)
        elif req.approval == ApprovalState.APPROVED:
            self._approved_count += 1
        return req

    def approve_pending(self, index: int = 0) -> ExecRequest | None:
        if index >= len(self._pending):
            return None
        req = self._pending.pop(index)
        req.approval = ApprovalState.APPROVED
        self._approved_count += 1
        return req

    def deny_pending(self, index: int = 0) -> ExecRequest | None:
        if index >= len(self._pending):
            return None
        req = self._pending.pop(index)
        req.approval = ApprovalState.DENIED
        return req
