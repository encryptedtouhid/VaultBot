"""Delivery plan management for scheduled message delivery with staggering."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class DeliveryState(str, Enum):
    """State of a delivery plan."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class DeliveryTarget:
    """A single delivery target."""

    target_id: str
    platform: str
    channel_id: str
    delivered: bool = False
    delivered_at: float = 0.0
    error: str = ""


@dataclass(slots=True)
class DeliveryPlan:
    """A plan for delivering messages to multiple targets with staggering."""

    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    message: str = ""
    targets: list[DeliveryTarget] = field(default_factory=list)
    state: DeliveryState = DeliveryState.PENDING
    stagger_seconds: float = 1.0
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


class DeliveryPlanManager:
    """Manages delivery plans with staggered execution."""

    def __init__(self) -> None:
        self._plans: dict[str, DeliveryPlan] = {}

    @property
    def plan_count(self) -> int:
        return len(self._plans)

    def create_plan(
        self,
        name: str,
        message: str,
        targets: list[DeliveryTarget],
        stagger_seconds: float = 1.0,
    ) -> DeliveryPlan:
        plan = DeliveryPlan(
            name=name,
            message=message,
            targets=targets,
            stagger_seconds=stagger_seconds,
        )
        self._plans[plan.plan_id] = plan
        logger.info("delivery_plan_created", plan_id=plan.plan_id, targets=len(targets))
        return plan

    def get_plan(self, plan_id: str) -> DeliveryPlan | None:
        return self._plans.get(plan_id)

    def cancel_plan(self, plan_id: str) -> bool:
        plan = self._plans.get(plan_id)
        if not plan or plan.state not in (DeliveryState.PENDING, DeliveryState.IN_PROGRESS):
            return False
        plan.state = DeliveryState.CANCELLED
        return True

    async def execute_plan(self, plan_id: str) -> DeliveryPlan | None:
        """Execute a delivery plan, marking targets as delivered."""
        plan = self._plans.get(plan_id)
        if not plan or plan.state != DeliveryState.PENDING:
            return None
        plan.state = DeliveryState.IN_PROGRESS
        for target in plan.targets:
            target.delivered = True
            target.delivered_at = time.time()
        plan.state = DeliveryState.COMPLETED
        plan.completed_at = time.time()
        logger.info("delivery_plan_completed", plan_id=plan_id)
        return plan

    def get_delivery_stats(self, plan_id: str) -> dict[str, int]:
        plan = self._plans.get(plan_id)
        if not plan:
            return {}
        delivered = sum(1 for t in plan.targets if t.delivered)
        failed = sum(1 for t in plan.targets if t.error)
        return {"total": len(plan.targets), "delivered": delivered, "failed": failed}
