"""Unit tests for deep plugin system."""

from __future__ import annotations

import pytest

from vaultbot.plugins.approval_workflow import (
    ApprovalState,
    PluginApprovalManager,
)
from vaultbot.plugins.channel_lifecycle import (
    ChannelEvent,
    ChannelLifecycleHook,
    ChannelLifecycleManager,
)
from vaultbot.plugins.config_schema import (
    ConfigSchemaValidator,
    PluginConfigSchema,
    SchemaField,
)


class TestChannelLifecycle:
    @pytest.mark.asyncio
    async def test_register_and_trigger(self) -> None:
        mgr = ChannelLifecycleManager()
        called = []

        async def on_connect(**kwargs: object) -> None:
            called.append("connected")

        mgr.register(
            ChannelLifecycleHook(
                channel="telegram",
                event=ChannelEvent.CONNECTED,
                handler=on_connect,
            )
        )
        count = await mgr.trigger("telegram", ChannelEvent.CONNECTED)
        assert count == 1
        assert called == ["connected"]

    def test_hook_count(self) -> None:
        mgr = ChannelLifecycleManager()

        async def handler(**kwargs: object) -> None:
            pass

        mgr.register(ChannelLifecycleHook(channel="tg", event=ChannelEvent.SETUP, handler=handler))
        mgr.register(ChannelLifecycleHook(channel="dc", event=ChannelEvent.SETUP, handler=handler))
        assert mgr.hook_count == 2


class TestConfigSchema:
    def test_validate_valid(self) -> None:
        validator = ConfigSchemaValidator()
        validator.register_schema(
            PluginConfigSchema(
                plugin_name="weather",
                fields=[
                    SchemaField(name="api_key", required=True),
                    SchemaField(name="units", choices=["metric", "imperial"]),
                ],
            )
        )
        errors = validator.validate("weather", {"api_key": "k", "units": "metric"})
        assert errors == []

    def test_validate_missing_required(self) -> None:
        validator = ConfigSchemaValidator()
        validator.register_schema(
            PluginConfigSchema(
                plugin_name="test",
                fields=[SchemaField(name="key", required=True)],
            )
        )
        errors = validator.validate("test", {})
        assert len(errors) == 1
        assert "Missing" in errors[0]

    def test_validate_invalid_choice(self) -> None:
        validator = ConfigSchemaValidator()
        validator.register_schema(
            PluginConfigSchema(
                plugin_name="test",
                fields=[SchemaField(name="mode", choices=["a", "b"])],
            )
        )
        errors = validator.validate("test", {"mode": "c"})
        assert len(errors) == 1

    def test_get_defaults(self) -> None:
        validator = ConfigSchemaValidator()
        validator.register_schema(
            PluginConfigSchema(
                plugin_name="test",
                fields=[
                    SchemaField(name="timeout", default=30),
                    SchemaField(name="name"),
                ],
            )
        )
        defaults = validator.get_defaults("test")
        assert defaults["timeout"] == 30
        assert "name" not in defaults


class TestPluginApproval:
    def test_request_and_approve(self) -> None:
        mgr = PluginApprovalManager()
        req = mgr.request_approval("weather", "install", requester="u1")
        assert req.state == ApprovalState.PENDING
        assert mgr.approve(req.request_id, approver="admin") is True
        assert req.state == ApprovalState.APPROVED

    def test_deny(self) -> None:
        mgr = PluginApprovalManager()
        req = mgr.request_approval("test", "exec")
        assert mgr.deny(req.request_id) is True
        assert req.state == ApprovalState.DENIED

    def test_list_pending(self) -> None:
        mgr = PluginApprovalManager()
        mgr.request_approval("a", "install")
        mgr.request_approval("b", "install")
        req = mgr.request_approval("c", "install")
        mgr.approve(req.request_id)
        assert mgr.pending_count == 2

    def test_filter_by_plugin(self) -> None:
        mgr = PluginApprovalManager()
        mgr.request_approval("weather", "install")
        mgr.request_approval("calendar", "install")
        pending = mgr.list_pending("weather")
        assert len(pending) == 1
