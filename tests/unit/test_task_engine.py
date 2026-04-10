"""Tests for the task/approval engine."""

import tempfile
from pathlib import Path

import pytest

from zenbot.core.task_engine import (
    Action,
    ActionResult,
    ApprovalStatus,
    TaskEngine,
)
from zenbot.security.audit import AuditLogger
from zenbot.security.policy import ActionSeverity, SecurityPolicy


@pytest.fixture
def engine() -> TaskEngine:
    with tempfile.TemporaryDirectory() as tmpdir:
        audit = AuditLogger(log_dir=Path(tmpdir))
        policy = SecurityPolicy()
        return TaskEngine(policy=policy, audit=audit)


@pytest.mark.asyncio
async def test_low_severity_auto_approved(engine: TaskEngine) -> None:
    action = Action(
        name="list_files",
        description="List files in directory",
        severity=ActionSeverity.LOW,
    )
    result = await engine.submit(action)
    assert result.status == ApprovalStatus.APPROVED


@pytest.mark.asyncio
async def test_info_severity_auto_approved(engine: TaskEngine) -> None:
    action = Action(
        name="get_weather",
        description="Check weather",
        severity=ActionSeverity.INFO,
    )
    result = await engine.submit(action)
    assert result.status == ApprovalStatus.APPROVED


@pytest.mark.asyncio
async def test_medium_denied_without_callback(engine: TaskEngine) -> None:
    """Without an approval callback, MEDIUM actions are denied by default."""
    action = Action(
        name="send_email",
        description="Send an email",
        severity=ActionSeverity.MEDIUM,
    )
    result = await engine.submit(action)
    assert result.status == ApprovalStatus.DENIED


@pytest.mark.asyncio
async def test_medium_approved_with_callback(engine: TaskEngine) -> None:
    async def approve_all(action: Action) -> ApprovalStatus:
        return ApprovalStatus.APPROVED

    engine.set_approval_callback(approve_all)

    action = Action(
        name="send_email",
        description="Send an email",
        severity=ActionSeverity.MEDIUM,
    )
    result = await engine.submit(action)
    assert result.status == ApprovalStatus.APPROVED


@pytest.mark.asyncio
async def test_medium_denied_with_callback(engine: TaskEngine) -> None:
    async def deny_all(action: Action) -> ApprovalStatus:
        return ApprovalStatus.DENIED

    engine.set_approval_callback(deny_all)

    action = Action(
        name="send_email",
        description="Send an email",
        severity=ActionSeverity.MEDIUM,
    )
    result = await engine.submit(action)
    assert result.status == ApprovalStatus.DENIED


@pytest.mark.asyncio
async def test_high_severity_requires_approval(engine: TaskEngine) -> None:
    action = Action(
        name="delete_file",
        description="Delete a file",
        severity=ActionSeverity.HIGH,
    )
    result = await engine.submit(action)
    assert result.status == ApprovalStatus.DENIED  # No callback = denied


def test_action_result_helpers() -> None:
    action = Action(name="test", description="test")

    denied = ActionResult.denied(action, "nope")
    assert denied.status == ApprovalStatus.DENIED
    assert denied.error == "nope"

    timed_out = ActionResult.timed_out(action)
    assert timed_out.status == ApprovalStatus.TIMED_OUT

    success = ActionResult.success("done")
    assert success.status == ApprovalStatus.APPROVED
    assert success.output == "done"
