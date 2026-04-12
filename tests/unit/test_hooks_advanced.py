"""Unit tests for enterprise hooks system."""

from __future__ import annotations

import pytest

from vaultbot.hooks.bundled.command_logger import CommandLoggerHook
from vaultbot.hooks.registry import HookDefinition, HookEvent, HookRegistry


class TestHookRegistry:
    @pytest.mark.asyncio
    async def test_register_and_trigger(self) -> None:
        reg = HookRegistry()
        called = []

        async def hook(**kwargs: object) -> None:
            called.append(True)

        reg.register(HookDefinition(name="test", event=HookEvent.ON_BOOT, callback=hook))
        count = await reg.trigger(HookEvent.ON_BOOT)
        assert count == 1
        assert len(called) == 1

    def test_unregister(self) -> None:
        reg = HookRegistry()

        async def hook(**kwargs: object) -> None:
            pass

        reg.register(HookDefinition(name="test", event=HookEvent.ON_BOOT, callback=hook))
        assert reg.unregister("test") is True
        assert reg.hook_count == 0

    @pytest.mark.asyncio
    async def test_priority_order(self) -> None:
        reg = HookRegistry()
        order: list[str] = []

        async def high(**kwargs: object) -> None:
            order.append("high")

        async def low(**kwargs: object) -> None:
            order.append("low")

        reg.register(HookDefinition(name="low", event=HookEvent.ON_BOOT, callback=low, priority=1))
        reg.register(
            HookDefinition(name="high", event=HookEvent.ON_BOOT, callback=high, priority=10)
        )
        await reg.trigger(HookEvent.ON_BOOT)
        assert order == ["high", "low"]

    @pytest.mark.asyncio
    async def test_error_doesnt_crash(self) -> None:
        reg = HookRegistry()

        async def bad(**kwargs: object) -> None:
            raise RuntimeError("boom")

        reg.register(HookDefinition(name="bad", event=HookEvent.ON_BOOT, callback=bad))
        count = await reg.trigger(HookEvent.ON_BOOT)
        assert count == 0

    def test_list_hooks(self) -> None:
        reg = HookRegistry()

        async def hook(**kwargs: object) -> None:
            pass

        reg.register(HookDefinition(name="a", event=HookEvent.ON_BOOT, callback=hook))
        reg.register(HookDefinition(name="b", event=HookEvent.ON_ERROR, callback=hook))
        assert len(reg.list_hooks(HookEvent.ON_BOOT)) == 1
        assert len(reg.list_hooks()) == 2


class TestCommandLoggerHook:
    @pytest.mark.asyncio
    async def test_log_command(self) -> None:
        hook = CommandLoggerHook()
        await hook.on_command(command="/help", user_id="u1")
        assert hook.log_count == 1
        assert hook.get_log()[0].command == "/help"
