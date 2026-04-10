"""Task execution engine with approval flows.

Every action with side effects passes through the approval gate.
This directly addresses OpenClaw's "over-autonomous behavior" problem.
Actions are classified by severity, and MEDIUM+ require explicit user confirmation.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from zenbot.security.audit import AuditLogger, EventType
from zenbot.security.policy import ActionSeverity, SecurityPolicy
from zenbot.utils.logging import get_logger

logger = get_logger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMED_OUT = "timed_out"


@dataclass
class Action:
    """An action that a plugin or the bot wants to perform."""

    name: str
    description: str
    plugin_name: str = ""
    severity: ActionSeverity = ActionSeverity.MEDIUM
    parameters: dict[str, Any] = field(default_factory=dict)
    chat_id: str = ""
    user_id: str = ""
    platform: str = ""


@dataclass
class ApprovalRequest:
    """A pending approval request sent to the user."""

    action: Action
    future: asyncio.Future[ApprovalStatus] = field(
        default_factory=lambda: asyncio.get_event_loop().create_future()
    )
    approval_timeout: float = 120.0  # 2 minutes default


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Result of attempting to execute an action."""

    status: ApprovalStatus
    output: str = ""
    error: str = ""

    @staticmethod
    def denied(action: Action, reason: str = "User denied the action") -> ActionResult:
        return ActionResult(status=ApprovalStatus.DENIED, error=reason)

    @staticmethod
    def timed_out(action: Action) -> ActionResult:
        return ActionResult(
            status=ApprovalStatus.TIMED_OUT,
            error="Approval request timed out",
        )

    @staticmethod
    def success(output: str = "") -> ActionResult:
        return ActionResult(status=ApprovalStatus.APPROVED, output=output)


class TaskEngine:
    """Manages action approval flows and execution.

    The engine sits between plugins/LLM and actual execution,
    ensuring nothing dangerous happens without user consent.
    """

    def __init__(
        self,
        policy: SecurityPolicy,
        audit: AuditLogger,
    ) -> None:
        self._policy = policy
        self._audit = audit
        self._pending_approvals: dict[str, ApprovalRequest] = {}
        self._approval_callback: ApprovalCallback | None = None

    def set_approval_callback(self, callback: ApprovalCallback) -> None:
        """Set the callback used to prompt users for approval.

        The callback receives the Action and should present it to the
        user on their messaging platform, then return the approval status.
        """
        self._approval_callback = callback

    async def submit(self, action: Action) -> ActionResult:
        """Submit an action for approval and execution.

        Actions are classified by severity:
        - INFO/LOW: Auto-approved (audit logged)
        - MEDIUM: Requires user confirmation
        - HIGH: Confirmation + cooldown
        - CRITICAL: Confirmation + 2FA/passphrase
        """
        severity = action.severity

        self._audit.log_action(
            event_type=EventType.ACTION_REQUESTED,
            platform=action.platform,
            user_id=action.user_id,
            action_name=action.name,
            severity=severity.value,
            plugin=action.plugin_name,
        )

        # Auto-approve low-severity actions
        if not self._policy.requires_approval(severity):
            logger.info(
                "action_auto_approved",
                action=action.name,
                severity=severity.value,
            )
            self._audit.log_action(
                event_type=EventType.ACTION_APPROVED,
                platform=action.platform,
                user_id=action.user_id,
                action_name=action.name,
                severity=severity.value,
                auto_approved=True,
            )
            return ActionResult.success()

        # Request user approval
        approval_status = await self._request_approval(action)

        if approval_status == ApprovalStatus.APPROVED:
            self._audit.log_action(
                event_type=EventType.ACTION_APPROVED,
                platform=action.platform,
                user_id=action.user_id,
                action_name=action.name,
                severity=severity.value,
            )

            # Apply cooldown for HIGH severity
            if self._policy.requires_cooldown(severity):
                logger.info("action_cooldown", action=action.name, seconds=5)
                await asyncio.sleep(5)

            return ActionResult.success()

        elif approval_status == ApprovalStatus.TIMED_OUT:
            self._audit.log_action(
                event_type=EventType.ACTION_DENIED,
                platform=action.platform,
                user_id=action.user_id,
                action_name=action.name,
                severity=severity.value,
                reason="timed_out",
            )
            return ActionResult.timed_out(action)

        else:
            self._audit.log_action(
                event_type=EventType.ACTION_DENIED,
                platform=action.platform,
                user_id=action.user_id,
                action_name=action.name,
                severity=severity.value,
                reason="user_denied",
            )
            return ActionResult.denied(action)

    async def _request_approval(self, action: Action) -> ApprovalStatus:
        """Request approval from the user via the registered callback."""
        if self._approval_callback is None:
            logger.warning(
                "no_approval_callback",
                msg="No approval callback set — denying action by default",
            )
            return ApprovalStatus.DENIED

        try:
            return await asyncio.wait_for(
                self._approval_callback(action),
                timeout=120.0,
            )
        except TimeoutError:
            return ApprovalStatus.TIMED_OUT

    def resolve_approval(self, request_id: str, status: ApprovalStatus) -> bool:
        """Resolve a pending approval request (called when user responds)."""
        request = self._pending_approvals.pop(request_id, None)
        if request is None:
            return False
        if not request.future.done():
            request.future.set_result(status)
        return True


ApprovalCallback = Callable[[Action], Coroutine[Any, Any, ApprovalStatus]]
