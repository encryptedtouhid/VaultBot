"""Plugin approval workflows."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ApprovalType(str, Enum):
    NATIVE = "native"
    HTTP = "http"
    CUSTOM = "custom"


class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass(slots=True)
class PluginApprovalRequest:
    request_id: str = ""
    plugin_name: str = ""
    action: str = ""
    approval_type: ApprovalType = ApprovalType.NATIVE
    state: ApprovalState = ApprovalState.PENDING
    requester: str = ""
    approver: str = ""
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 3600.0


class PluginApprovalManager:
    """Manages plugin approval workflows."""

    def __init__(self) -> None:
        self._requests: dict[str, PluginApprovalRequest] = {}
        self._counter = 0

    def request_approval(
        self,
        plugin_name: str,
        action: str,
        requester: str = "",
        approval_type: ApprovalType = ApprovalType.NATIVE,
    ) -> PluginApprovalRequest:
        self._counter += 1
        req = PluginApprovalRequest(
            request_id=f"papr_{self._counter}",
            plugin_name=plugin_name,
            action=action,
            requester=requester,
            approval_type=approval_type,
        )
        self._requests[req.request_id] = req
        return req

    def approve(self, request_id: str, approver: str = "") -> bool:
        req = self._requests.get(request_id)
        if not req or req.state != ApprovalState.PENDING:
            return False
        req.state = ApprovalState.APPROVED
        req.approver = approver
        return True

    def deny(self, request_id: str, approver: str = "") -> bool:
        req = self._requests.get(request_id)
        if not req or req.state != ApprovalState.PENDING:
            return False
        req.state = ApprovalState.DENIED
        req.approver = approver
        return True

    def list_pending(self, plugin_name: str = "") -> list[PluginApprovalRequest]:
        pending = [r for r in self._requests.values() if r.state == ApprovalState.PENDING]
        if plugin_name:
            pending = [r for r in pending if r.plugin_name == plugin_name]
        return pending

    @property
    def pending_count(self) -> int:
        return len(self.list_pending())
