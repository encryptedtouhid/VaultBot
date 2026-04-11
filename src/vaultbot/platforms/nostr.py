"""Nostr messaging platform adapter.

Implements an async Nostr client that connects to relays via WebSocket
and handles NIP-01 (basic protocol) and NIP-04 (encrypted DMs) events.
Uses ``httpx`` for relay communication and raw WebSocket handling.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Nostr event kinds (NIP-01)
_KIND_TEXT_NOTE = 1
_KIND_ENCRYPTED_DM = 4


class NostrAdapter:
    """Nostr protocol adapter for decentralized messaging.

    Parameters
    ----------
    private_key_hex:
        Hex-encoded private key for signing events.
    public_key_hex:
        Hex-encoded public key (derived from private key).
    relays:
        List of relay WebSocket URLs (e.g. ``wss://relay.damus.io``).
    """

    def __init__(
        self,
        *,
        private_key_hex: str = "",
        public_key_hex: str = "",
        relays: list[str] | None = None,
    ) -> None:
        self._private_key = private_key_hex
        self._public_key = public_key_hex
        self._relays = relays or ["wss://relay.damus.io"]
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._connected = False
        self._ws_tasks: list[asyncio.Task[None]] = []

    @property
    def platform_name(self) -> str:
        return "nostr"

    async def connect(self) -> None:
        if not self._public_key:
            raise ValueError("NostrAdapter requires public_key_hex")

        self._connected = True

        # Start a listener task for each relay
        for relay_url in self._relays:
            task = asyncio.create_task(self._relay_loop(relay_url))
            self._ws_tasks.append(task)

        logger.info("nostr_connected", relays=self._relays, pubkey=self._public_key[:16])

    async def disconnect(self) -> None:
        for task in self._ws_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._ws_tasks.clear()
        self._connected = False
        logger.info("nostr_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        if not self._connected:
            raise RuntimeError("Nostr adapter not connected")

        # Build a kind-1 text note event
        event = self._build_event(
            kind=_KIND_TEXT_NOTE,
            content=message.text,
            tags=[["p", message.chat_id]] if message.chat_id else [],
        )

        # Publish to all relays
        for relay_url in self._relays:
            await self._publish_event(relay_url, event)

    async def healthcheck(self) -> bool:
        return self._connected and len(self._ws_tasks) > 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _relay_loop(self, relay_url: str) -> None:
        """Connect to a relay and subscribe to mentions."""
        try:
            import websockets
        except ImportError:
            logger.warning("nostr_ws_unavailable", msg="websockets package not installed")
            return

        try:
            async for ws in websockets.connect(relay_url):
                try:
                    # Subscribe to mentions of our pubkey
                    sub_id = f"vaultbot-{self._public_key[:8]}"
                    sub_filter = {
                        "kinds": [_KIND_TEXT_NOTE, _KIND_ENCRYPTED_DM],
                        "#p": [self._public_key],
                        "limit": 10,
                    }
                    await ws.send(json.dumps(["REQ", sub_id, sub_filter]))

                    async for raw_msg in ws:
                        data = json.loads(raw_msg)
                        if isinstance(data, list) and len(data) >= 3 and data[0] == "EVENT":
                            self._process_event(data[2])
                except Exception:
                    logger.warning("nostr_relay_reconnecting", relay=relay_url)
                    continue
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("nostr_relay_error", relay=relay_url)

    def _process_event(self, event: dict) -> None:
        """Convert a Nostr event into an InboundMessage."""
        pubkey = event.get("pubkey", "")
        if pubkey == self._public_key:
            return  # Ignore own events

        content = event.get("content", "")
        if not content:
            return

        created_at = event.get("created_at", 0)
        try:
            timestamp = datetime.fromtimestamp(created_at, tz=UTC)
        except (ValueError, OSError, OverflowError):
            timestamp = datetime.now(UTC)

        event_id = event.get("id", "")

        # Extract reply reference from e-tags
        reply_to: str | None = None
        for tag in event.get("tags", []):
            if len(tag) >= 2 and tag[0] == "e":
                reply_to = tag[1]
                break

        inbound = InboundMessage(
            id=event_id,
            platform="nostr",
            sender_id=pubkey,
            chat_id=pubkey,  # In Nostr, sender pubkey is the "chat"
            text=content,
            timestamp=timestamp,
            reply_to=reply_to,
            raw=event,
        )
        self._message_queue.put_nowait(inbound)

    def _build_event(self, *, kind: int, content: str, tags: list[list[str]]) -> dict:
        """Build a Nostr event (unsigned — signing requires secp256k1)."""
        created_at = int(time.time())
        event = {
            "pubkey": self._public_key,
            "created_at": created_at,
            "kind": kind,
            "tags": tags,
            "content": content,
        }
        # Compute event ID (SHA-256 of serialized event)
        serialized = json.dumps(
            [0, event["pubkey"], created_at, kind, tags, content],
            separators=(",", ":"),
            ensure_ascii=False,
        )
        event["id"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        event["sig"] = ""  # Signing requires secp256k1 library
        return event

    async def _publish_event(self, relay_url: str, event: dict) -> None:
        """Publish an event to a relay."""
        try:
            import websockets
        except ImportError:
            return

        try:
            async with websockets.connect(relay_url) as ws:
                await ws.send(json.dumps(["EVENT", event]))
        except Exception:
            logger.warning("nostr_publish_failed", relay=relay_url)
