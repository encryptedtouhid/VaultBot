"""WhatsApp Cloud API messaging platform adapter.

Uses the Meta WhatsApp Business Cloud API directly via httpx.
Requires a webhook endpoint to receive incoming messages.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx

from zenbot.core.message import InboundMessage, OutboundMessage
from zenbot.utils.logging import get_logger

logger = get_logger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


class WhatsAppAdapter:
    """WhatsApp Cloud API adapter.

    Incoming messages are fed via `receive_webhook()` from an external
    webhook server (e.g., FastAPI/Starlette). This adapter does not
    run its own HTTP server to keep concerns separated.
    """

    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        verify_token: str = "",
    ) -> None:
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        self._verify_token = verify_token
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._client: httpx.AsyncClient | None = None

    @property
    def platform_name(self) -> str:
        return "whatsapp"

    async def connect(self) -> None:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=GRAPH_API_URL,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        logger.info("whatsapp_connected", phone_number_id=self._phone_number_id)

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
        logger.info("whatsapp_disconnected")

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """Verify the webhook subscription from Meta.

        Returns the challenge string if valid, None otherwise.
        """
        if mode == "subscribe" and token == self._verify_token:
            return challenge
        return None

    async def receive_webhook(self, payload: dict) -> None:  # type: ignore[type-arg]
        """Process an incoming webhook payload from Meta.

        Call this from your webhook endpoint handler.
        """
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" not in value:
                    continue

                for msg in value["messages"]:
                    if msg.get("type") != "text":
                        continue

                    timestamp = datetime.fromtimestamp(
                        int(msg.get("timestamp", 0)), tz=UTC
                    )

                    inbound = InboundMessage(
                        id=msg["id"],
                        platform="whatsapp",
                        sender_id=msg["from"],
                        chat_id=msg["from"],  # WhatsApp uses phone number as chat ID
                        text=msg.get("text", {}).get("body", ""),
                        timestamp=timestamp,
                        reply_to=msg.get("context", {}).get("id"),
                        raw=msg,
                    )
                    await self._message_queue.put(inbound)

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive via webhooks."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a text message via WhatsApp Cloud API."""
        if not self._client:
            raise RuntimeError("WhatsApp adapter not connected")

        payload = {
            "messaging_product": "whatsapp",
            "to": message.chat_id,
            "type": "text",
            "text": {"body": message.text},
        }

        if message.reply_to:
            payload["context"] = {"message_id": message.reply_to}

        response = await self._client.post(
            f"/{self._phone_number_id}/messages",
            json=payload,
        )

        if response.status_code != 200:
            logger.error(
                "whatsapp_send_error",
                status=response.status_code,
                body=response.text,
            )
            response.raise_for_status()

    async def healthcheck(self) -> bool:
        """Check if the WhatsApp API is reachable."""
        if not self._client:
            return False
        try:
            response = await self._client.get(f"/{self._phone_number_id}")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
