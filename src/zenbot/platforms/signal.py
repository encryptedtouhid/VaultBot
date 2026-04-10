"""Signal messaging platform adapter.

Uses signal-cli's JSON-RPC interface via stdin/stdout or TCP socket.
This avoids the signalbot library dependency and gives us direct control.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx

from zenbot.core.message import InboundMessage, OutboundMessage
from zenbot.utils.logging import get_logger

logger = get_logger(__name__)


class SignalAdapter:
    """Signal adapter using signal-cli's JSON-RPC API.

    Requires signal-cli to be running in JSON-RPC mode:
        signal-cli -a +1234567890 jsonRpc --socket /tmp/signal-cli.sock

    Or in TCP mode:
        signal-cli -a +1234567890 jsonRpc --tcp localhost:7583
    """

    def __init__(
        self,
        *,
        account: str,
        signal_cli_url: str = "http://localhost:7583",
    ) -> None:
        self._account = account
        self._signal_cli_url = signal_cli_url
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._client: httpx.AsyncClient | None = None
        self._polling = False

    @property
    def platform_name(self) -> str:
        return "signal"

    async def connect(self) -> None:
        """Initialize the HTTP client for signal-cli JSON-RPC."""
        self._client = httpx.AsyncClient(
            base_url=self._signal_cli_url,
            timeout=30.0,
        )
        self._polling = True
        asyncio.create_task(self._poll_messages())
        logger.info("signal_connected", account=self._account)

    async def disconnect(self) -> None:
        """Stop polling and close the client."""
        self._polling = False
        if self._client:
            await self._client.aclose()
        logger.info("signal_disconnected")

    async def _jsonrpc_call(self, method: str, params: dict | None = None) -> dict:  # type: ignore[type-arg]
        """Make a JSON-RPC call to signal-cli."""
        if not self._client:
            raise RuntimeError("Signal adapter not connected")

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1,
        }

        response = await self._client.post("/api/v1/rpc", json=payload)
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise RuntimeError(f"signal-cli error: {result['error']}")

        return result.get("result", {})

    async def _poll_messages(self) -> None:
        """Poll signal-cli for new messages."""
        while self._polling:
            try:
                result = await self._jsonrpc_call(
                    "receive",
                    {"account": self._account, "timeout": 5},
                )

                for envelope in result if isinstance(result, list) else []:
                    await self._process_envelope(envelope)

            except httpx.HTTPError as e:
                logger.error("signal_poll_error", error=str(e))
            except Exception as e:
                logger.error("signal_poll_unexpected_error", error=str(e))

            await asyncio.sleep(1.0)

    async def _process_envelope(self, envelope: dict) -> None:  # type: ignore[type-arg]
        """Process a single signal-cli message envelope."""
        data_message = envelope.get("dataMessage")
        if not data_message or not data_message.get("message"):
            return

        source = envelope.get("source", "")
        timestamp_ms = data_message.get("timestamp", 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)

        # Use group ID if present, otherwise sender as chat ID
        group_info = data_message.get("groupInfo", {})
        chat_id = group_info.get("groupId", source)

        inbound = InboundMessage(
            id=str(timestamp_ms),
            platform="signal",
            sender_id=source,
            chat_id=chat_id,
            text=data_message["message"],
            timestamp=timestamp,
            reply_to=None,
            raw=envelope,
        )
        await self._message_queue.put(inbound)

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from Signal."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a message via Signal."""
        # Determine if it's a group or individual message
        if message.chat_id.startswith("+"):
            params = {
                "account": self._account,
                "recipient": [message.chat_id],
                "message": message.text,
            }
        else:
            params = {
                "account": self._account,
                "groupId": message.chat_id,
                "message": message.text,
            }

        await self._jsonrpc_call("send", params)

    async def healthcheck(self) -> bool:
        """Check if signal-cli is responsive."""
        try:
            await self._jsonrpc_call("version")
            return True
        except Exception:
            return False
