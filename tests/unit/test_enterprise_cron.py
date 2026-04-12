"""Unit tests for enterprise cron features."""

from __future__ import annotations

import pytest

from vaultbot.cron.delivery_plan import (
    DeliveryPlanManager,
    DeliveryState,
    DeliveryTarget,
)
from vaultbot.cron.job_store import InMemoryJobStore, JobStore
from vaultbot.cron.scheduler import CronJob


class TestDeliveryPlan:
    def test_create_plan(self) -> None:
        mgr = DeliveryPlanManager()
        targets = [
            DeliveryTarget(target_id="t1", platform="telegram", channel_id="c1"),
            DeliveryTarget(target_id="t2", platform="discord", channel_id="c2"),
        ]
        plan = mgr.create_plan("test", "hello", targets)
        assert plan.state == DeliveryState.PENDING
        assert mgr.plan_count == 1

    def test_cancel_plan(self) -> None:
        mgr = DeliveryPlanManager()
        plan = mgr.create_plan("test", "msg", [])
        assert mgr.cancel_plan(plan.plan_id) is True
        assert mgr.get_plan(plan.plan_id).state == DeliveryState.CANCELLED

    def test_cancel_completed_fails(self) -> None:
        mgr = DeliveryPlanManager()
        plan = mgr.create_plan("test", "msg", [])
        plan.state = DeliveryState.COMPLETED
        assert mgr.cancel_plan(plan.plan_id) is False

    @pytest.mark.asyncio
    async def test_execute_plan(self) -> None:
        mgr = DeliveryPlanManager()
        targets = [DeliveryTarget(target_id="t1", platform="tg", channel_id="c1")]
        plan = mgr.create_plan("test", "hello", targets)
        result = await mgr.execute_plan(plan.plan_id)
        assert result is not None
        assert result.state == DeliveryState.COMPLETED
        assert result.targets[0].delivered is True

    @pytest.mark.asyncio
    async def test_execute_unknown_returns_none(self) -> None:
        mgr = DeliveryPlanManager()
        assert await mgr.execute_plan("nope") is None

    def test_delivery_stats(self) -> None:
        mgr = DeliveryPlanManager()
        targets = [
            DeliveryTarget(target_id="t1", platform="tg", channel_id="c1", delivered=True),
            DeliveryTarget(target_id="t2", platform="tg", channel_id="c2"),
        ]
        plan = mgr.create_plan("test", "msg", targets)
        stats = mgr.get_delivery_stats(plan.plan_id)
        assert stats["total"] == 2
        assert stats["delivered"] == 1


class TestInMemoryJobStore:
    def test_is_job_store(self) -> None:
        assert isinstance(InMemoryJobStore(), JobStore)

    @pytest.mark.asyncio
    async def test_save_and_load(self) -> None:
        store = InMemoryJobStore()
        job = CronJob(id="j1", name="test", schedule="every 5m", action="noop")
        await store.save_job(job)
        loaded = await store.load_job("j1")
        assert loaded is not None
        assert loaded.name == "test"

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        store = InMemoryJobStore()
        job = CronJob(id="j1", name="test", schedule="every 5m", action="noop")
        await store.save_job(job)
        assert await store.delete_job("j1") is True
        assert await store.load_job("j1") is None

    @pytest.mark.asyncio
    async def test_list_jobs(self) -> None:
        store = InMemoryJobStore()
        await store.save_job(CronJob(id="j1", name="a", schedule="every 5m", action="x"))
        await store.save_job(CronJob(id="j2", name="b", schedule="every 1h", action="y"))
        jobs = await store.list_jobs()
        assert len(jobs) == 2
