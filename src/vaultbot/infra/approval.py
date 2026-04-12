"""Approval handlers with delivery."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass(slots=True)
class ApprovalRequest:
    request_id: str = ""
    action: str = ""
    requester: str = ""
    approver: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    decided_at: float = 0.0
    ttl_seconds: float = 3600.0

    @property
    def is_expired(self) -> bool:
        return (
            time.time() - self.created_at
        ) > self.ttl_seconds and self.status == ApprovalStatus.PENDING


class ApprovalManager:
    """Manages approval requests."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._counter = 0

    def create(self, action: str, requester: str = "") -> ApprovalRequest:
        self._counter += 1
        req = ApprovalRequest(request_id=f"apr_{self._counter}", action=action, requester=requester)
        self._requests[req.request_id] = req
        return req

    def approve(self, request_id: str, approver: str = "") -> bool:
        req = self._requests.get(request_id)
        if not req or req.status != ApprovalStatus.PENDING:
            return False
        req.status = ApprovalStatus.APPROVED
        req.approver = approver
        req.decided_at = time.time()
        return True

    def deny(self, request_id: str, approver: str = "") -> bool:
        req = self._requests.get(request_id)
        if not req or req.status != ApprovalStatus.PENDING:
            return False
        req.status = ApprovalStatus.DENIED
        req.approver = approver
        req.decided_at = time.time()
        return True

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def list_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]

    @property
    def pending_count(self) -> int:
        return len(self.list_pending())
