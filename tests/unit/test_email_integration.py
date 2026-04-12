"""Unit tests for email integration."""

from __future__ import annotations

import pytest

from vaultbot.integrations.email_client import EmailClient, EmailConfig, EmailMessage


class TestEmailMessage:
    def test_defaults(self) -> None:
        msg = EmailMessage()
        assert msg.subject == ""
        assert msg.recipients == []

    def test_with_values(self) -> None:
        msg = EmailMessage(subject="Test", body="Hello", recipients=["a@b.com"])
        assert msg.subject == "Test"
        assert len(msg.recipients) == 1


class TestEmailClient:
    def test_not_connected_by_default(self) -> None:
        config = EmailConfig(imap_host="imap.test.com", smtp_host="smtp.test.com")
        client = EmailClient(config)
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_connect_disconnect(self) -> None:
        config = EmailConfig()
        client = EmailClient(config)
        await client.connect()
        assert client.is_connected
        await client.disconnect()
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_send_requires_connection(self) -> None:
        client = EmailClient(EmailConfig())
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.send(EmailMessage(subject="Test"))

    @pytest.mark.asyncio
    async def test_send_increments_count(self) -> None:
        client = EmailClient(EmailConfig())
        await client.connect()
        await client.send(EmailMessage(subject="Test", recipients=["a@b.com"]))
        assert client.sent_count == 1

    @pytest.mark.asyncio
    async def test_fetch_requires_connection(self) -> None:
        client = EmailClient(EmailConfig())
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.fetch_inbox()

    @pytest.mark.asyncio
    async def test_search_requires_connection(self) -> None:
        client = EmailClient(EmailConfig())
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.search("test")


class TestGmailProvider:
    def test_provider_name(self) -> None:
        from vaultbot.integrations.gmail import GmailConfig, GmailProvider

        p = GmailProvider(GmailConfig())
        assert p.provider_name == "gmail"

    @pytest.mark.asyncio
    async def test_connect_disconnect(self) -> None:
        from vaultbot.integrations.gmail import GmailConfig, GmailProvider

        p = GmailProvider(GmailConfig())
        await p.connect()
        assert p.is_connected
        await p.disconnect()
        assert not p.is_connected

    @pytest.mark.asyncio
    async def test_send_requires_connection(self) -> None:
        from vaultbot.integrations.gmail import GmailConfig, GmailProvider

        p = GmailProvider(GmailConfig())
        with pytest.raises(RuntimeError, match="Not connected"):
            await p.send(EmailMessage(subject="Test"))

    @pytest.mark.asyncio
    async def test_list_requires_connection(self) -> None:
        from vaultbot.integrations.gmail import GmailConfig, GmailProvider

        p = GmailProvider(GmailConfig())
        with pytest.raises(RuntimeError, match="Not connected"):
            await p.list_messages()
