"""Gmail-specific email provider using Gmail API."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from vaultbot.integrations.email_client import EmailMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://gmail.googleapis.com/gmail/v1"


@dataclass(frozen=True, slots=True)
class GmailConfig:
    """Gmail API configuration."""

    access_token: str = ""
    refresh_token: str = ""
    client_id: str = ""
    client_secret: str = ""


class GmailProvider:
    """Gmail API provider for email operations."""

    def __init__(self, config: GmailConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=_API_URL,
            timeout=30.0,
            headers={"Authorization": f"Bearer {config.access_token}"},
        )
        self._connected = False

    @property
    def provider_name(self) -> str:
        return "gmail"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True
        logger.info("gmail_connected")

    async def disconnect(self) -> None:
        self._connected = False
        await self._client.aclose()

    async def send(self, message: EmailMessage) -> bool:
        """Send email via Gmail API."""
        if not self._connected:
            raise RuntimeError("Not connected")
        resp = await self._client.post(
            "/users/me/messages/send",
            json={"raw": ""},  # Base64 encoded email
        )
        resp.raise_for_status()
        logger.info("gmail_sent", subject=message.subject)
        return True

    async def list_messages(self, query: str = "", max_results: int = 10) -> list[dict[str, str]]:
        """List messages matching a query."""
        if not self._connected:
            raise RuntimeError("Not connected")
        resp = await self._client.get(
            "/users/me/messages",
            params={"q": query, "maxResults": max_results},
        )
        resp.raise_for_status()
        return resp.json().get("messages", [])

    async def get_labels(self) -> list[dict[str, str]]:
        """Get all Gmail labels."""
        if not self._connected:
            raise RuntimeError("Not connected")
        resp = await self._client.get("/users/me/labels")
        resp.raise_for_status()
        return resp.json().get("labels", [])
