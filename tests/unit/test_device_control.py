"""Unit tests for device control and phone integration."""

from __future__ import annotations

import pytest

from vaultbot.integrations.device_control import (
    DeviceAction,
    DeviceCapability,
    DeviceCommand,
    DeviceControlManager,
    DeviceProvider,
    DeviceResult,
)
from vaultbot.integrations.phone import CallState, PhoneManager, SMSMessage


class MockDeviceProvider:
    def __init__(self, name: str = "mock_device") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    def capabilities(self) -> list[DeviceCapability]:
        return [DeviceCapability.SCREEN_CAPTURE, DeviceCapability.CLIPBOARD]

    async def execute(self, command: DeviceCommand) -> DeviceResult:
        return DeviceResult(success=True, action=command.action)


class TestDeviceControl:
    def test_action_enum(self) -> None:
        assert DeviceAction.SCREENSHOT.value == "screenshot"

    def test_mock_is_provider(self) -> None:
        assert isinstance(MockDeviceProvider(), DeviceProvider)

    def test_register_provider(self) -> None:
        mgr = DeviceControlManager()
        mgr.register_provider(MockDeviceProvider("test"))
        assert "test" in mgr.list_providers()

    def test_get_capabilities(self) -> None:
        mgr = DeviceControlManager()
        mgr.register_provider(MockDeviceProvider())
        caps = mgr.get_capabilities()
        assert DeviceCapability.SCREEN_CAPTURE in caps

    @pytest.mark.asyncio
    async def test_execute(self) -> None:
        mgr = DeviceControlManager()
        mgr.register_provider(MockDeviceProvider())
        result = await mgr.execute(DeviceCommand(action=DeviceAction.SCREENSHOT))
        assert result.success is True
        assert mgr.execution_count == 1

    @pytest.mark.asyncio
    async def test_execute_no_provider(self) -> None:
        mgr = DeviceControlManager()
        result = await mgr.execute(DeviceCommand(action=DeviceAction.SCREENSHOT))
        assert result.success is False


class TestPhoneManager:
    @pytest.mark.asyncio
    async def test_send_sms(self) -> None:
        mgr = PhoneManager()
        result = await mgr.send_sms(SMSMessage(to="+1234", body="hello"))
        assert result is True
        assert mgr.sms_count == 1

    @pytest.mark.asyncio
    async def test_initiate_call(self) -> None:
        mgr = PhoneManager()
        call = await mgr.initiate_call("+1234")
        assert call.state == CallState.RINGING
        assert mgr.active_call_count == 1

    @pytest.mark.asyncio
    async def test_end_call(self) -> None:
        mgr = PhoneManager()
        call = await mgr.initiate_call("+1234")
        result = await mgr.end_call(call.call_id)
        assert result is True
        assert mgr.active_call_count == 0

    @pytest.mark.asyncio
    async def test_end_unknown_call(self) -> None:
        mgr = PhoneManager()
        result = await mgr.end_call("nonexistent")
        assert result is False
