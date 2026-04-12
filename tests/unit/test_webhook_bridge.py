"""Unit tests for webhook bridge."""

from __future__ import annotations

import pytest

from vaultbot.platforms.base import PlatformAdapter
from vaultbot.platforms.webhook_bridge import WebhookBridge, WebhookBridgeConfig, WebhookMapping


class TestWebhookBridge:
    def test_platform_name(self) -> None:
        bridge = WebhookBridge()
        assert bridge.platform_name == "webhook"

    def test_custom_name(self) -> None:
        bridge = WebhookBridge(WebhookBridgeConfig(name="jira"))
        assert bridge.platform_name == "jira"

    def test_is_platform_adapter(self) -> None:
        assert isinstance(WebhookBridge(), PlatformAdapter)

    @pytest.mark.asyncio
    async def test_healthcheck(self) -> None:
        bridge = WebhookBridge()
        assert await bridge.healthcheck() is False
        await bridge.connect()
        assert await bridge.healthcheck() is True

    def test_ingest_payload(self) -> None:
        bridge = WebhookBridge()
        msg = bridge.ingest_payload({"text": "hello", "user": {"id": "u1"}, "channel": "c1"})
        assert msg is not None
        assert msg.text == "hello"

    def test_ingest_custom_mapping(self) -> None:
        config = WebhookBridgeConfig(
            mapping=WebhookMapping(content_path="body", user_id_path="sender")
        )
        bridge = WebhookBridge(config)
        msg = bridge.ingest_payload({"body": "custom", "sender": "u2"})
        assert msg is not None
        assert msg.text == "custom"

    def test_ingest_empty_returns_none(self) -> None:
        bridge = WebhookBridge()
        msg = bridge.ingest_payload({"other": "data"})
        assert msg is None

    def test_extract_nested_path(self) -> None:
        result = WebhookBridge._extract_path({"a": {"b": {"c": "deep"}}}, "a.b.c")
        assert result == "deep"
