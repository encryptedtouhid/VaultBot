"""Matrix messaging platform adapter.

Implements an async Matrix client using the Client-Server API directly
via ``httpx``.  Supports homeserver discovery, room joins, text message
sending/receiving, and long-poll ``/sync`` for real-time updates.

No third-party Matrix SDK is required — the adapter speaks the Matrix
REST API, keeping the dependency footprint minimal and auditable.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

# Matrix Client-Server API paths
_LOGIN = "/_matrix/client/v3/login"
_SYNC = "/_matrix/client/v3/sync"
_SEND_EVENT = "/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}"
_JOIN_ROOM = "/_matrix/client/v3/join/{room_id}"
_WHOAMI = "/_matrix/client/v3/account/whoami"

# Sync timeout in milliseconds (30 s long-poll)
_SYNC_TIMEOUT_MS = 30_000


class MatrixAdapter:
    """Matrix bot adapter using the Client-Server REST API.

    Parameters
    ----------
    homeserver:
        Full URL of the Matrix homeserver (e.g. ``https://matrix.org``).
    access_token:
        A pre-provisioned access token for the bot account.  Alternatively
        supply ``user_id`` + ``password`` and the adapter will call
        ``/login`` during :meth:`connect`.
    user_id:
        Matrix user ID (e.g. ``@vaultbot:matrix.org``).  Required when
        using password login; ignored when *access_token* is provided.
    password:
        Password for login.  Ignored when *access_token* is provided.
    rooms:
        List of room IDs or aliases to auto-join on connect.
    """

    def __init__(
        self,
        *,
        homeserver: str,
        access_token: str = "",
        user_id: str = "",
        password: str = "",
        rooms: list[str] | None = None,
    ) -> None:
        # Strip trailing slash for consistent URL building
        self._homeserver = homeserver.rstrip("/")
        self._access_token = access_token
        self._user_id = user_id
        self._password = password
        self._rooms = rooms or []

        self._client: httpx.AsyncClient | None = None
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._connected = False
        self._sync_task: asyncio.Task[None] | None = None
        self._next_batch: str = ""
        self._txn_counter: int = 0

    # ------------------------------------------------------------------
    # PlatformAdapter protocol
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "matrix"

    async def connect(self) -> None:
        """Authenticate with the homeserver and start the sync loop."""
        self._client = httpx.AsyncClient(timeout=60.0)

        # Authenticate if no access token provided
        if not self._access_token:
            if not self._user_id or not self._password:
                raise ValueError("MatrixAdapter requires either access_token or user_id+password")
            await self._login()

        # Resolve our own user ID if not known
        if not self._user_id:
            await self._resolve_user_id()

        # Auto-join configured rooms
        for room in self._rooms:
            await self._join_room(room)

        # Start long-poll sync loop
        self._sync_task = asyncio.create_task(self._sync_loop())
        self._connected = True
        logger.info(
            "matrix_connected",
            homeserver=self._homeserver,
            user_id=self._user_id,
        )

    async def disconnect(self) -> None:
        """Stop the sync loop and close the HTTP client."""
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.aclose()
            self._client = None

        self._connected = False
        logger.info("matrix_disconnected")

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from Matrix rooms."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a text message to a Matrix room."""
        if not self._client or not self._access_token:
            raise RuntimeError("Matrix adapter not connected")

        self._txn_counter += 1
        txn_id = f"vaultbot_{self._txn_counter}"

        url = self._url(_SEND_EVENT.format(room_id=message.chat_id, txn_id=txn_id))
        body = {
            "msgtype": "m.text",
            "body": message.text,
        }

        resp = await self._client.put(
            url,
            json=body,
            headers=self._auth_headers(),
        )
        if resp.status_code not in (200, 201):
            logger.error(
                "matrix_send_failed",
                room_id=message.chat_id,
                status=resp.status_code,
                body=resp.text[:200],
            )

    async def healthcheck(self) -> bool:
        """Check if the Matrix connection is healthy by calling /account/whoami."""
        if not self._client or not self._access_token:
            return False
        try:
            resp = await self._client.get(
                self._url(_WHOAMI),
                headers=self._auth_headers(),
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """Build a full URL from the homeserver and API path."""
        return f"{self._homeserver}{path}"

    def _auth_headers(self) -> dict[str, str]:
        """Return the Authorization header."""
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _login(self) -> None:
        """Authenticate via password login and store the access token."""
        assert self._client is not None
        resp = await self._client.post(
            self._url(_LOGIN),
            json={
                "type": "m.login.password",
                "user": self._user_id,
                "password": self._password,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Matrix login failed ({resp.status_code}): {resp.text[:200]}")
        data = resp.json()
        self._access_token = data["access_token"]
        self._user_id = data.get("user_id", self._user_id)
        logger.info("matrix_login_success", user_id=self._user_id)

    async def _resolve_user_id(self) -> None:
        """Resolve the bot's own user ID via /account/whoami."""
        assert self._client is not None
        resp = await self._client.get(
            self._url(_WHOAMI),
            headers=self._auth_headers(),
        )
        if resp.status_code == 200:
            self._user_id = resp.json().get("user_id", "")

    async def _join_room(self, room_id_or_alias: str) -> None:
        """Join a Matrix room by ID or alias."""
        assert self._client is not None
        url = self._url(_JOIN_ROOM.format(room_id=room_id_or_alias))
        resp = await self._client.post(
            url,
            json={},
            headers=self._auth_headers(),
        )
        if resp.status_code == 200:
            logger.info("matrix_room_joined", room=room_id_or_alias)
        else:
            logger.warning(
                "matrix_room_join_failed",
                room=room_id_or_alias,
                status=resp.status_code,
            )

    async def _sync_loop(self) -> None:
        """Long-poll /sync and dispatch incoming messages."""
        try:
            while self._client:
                params: dict[str, str | int] = {"timeout": _SYNC_TIMEOUT_MS}
                if self._next_batch:
                    params["since"] = self._next_batch

                try:
                    resp = await self._client.get(
                        self._url(_SYNC),
                        params=params,
                        headers=self._auth_headers(),
                    )
                except (httpx.ReadTimeout, httpx.ConnectTimeout):
                    continue
                except Exception:
                    logger.exception("matrix_sync_error")
                    await asyncio.sleep(5)
                    continue

                if resp.status_code != 200:
                    await asyncio.sleep(5)
                    continue

                data = resp.json()
                self._next_batch = data.get("next_batch", self._next_batch)

                # Process room events
                rooms = data.get("rooms", {}).get("join", {})
                for room_id, room_data in rooms.items():
                    timeline = room_data.get("timeline", {})
                    events = timeline.get("events", [])
                    for event in events:
                        self._process_event(room_id, event)

        except asyncio.CancelledError:
            return

    def _process_event(self, room_id: str, event: dict) -> None:
        """Convert a Matrix room event into an InboundMessage and enqueue it."""
        if event.get("type") != "m.room.message":
            return

        sender = event.get("sender", "")
        # Ignore own messages
        if sender == self._user_id:
            return

        content = event.get("content", {})
        msgtype = content.get("msgtype", "")

        # Only handle text messages for now
        if msgtype != "m.text":
            return

        body = content.get("body", "")
        if not body:
            return

        # Parse timestamp (milliseconds since epoch)
        origin_ts = event.get("origin_server_ts", 0)
        try:
            timestamp = datetime.fromtimestamp(origin_ts / 1000, tz=UTC)
        except (ValueError, OSError, OverflowError):
            timestamp = datetime.now(UTC)

        event_id = event.get("event_id", "")

        # Check for reply (m.relates_to with m.in_reply_to)
        reply_to: str | None = None
        relates_to = content.get("m.relates_to", {})
        in_reply_to = relates_to.get("m.in_reply_to", {})
        if in_reply_to:
            reply_to = in_reply_to.get("event_id")

        inbound = InboundMessage(
            id=event_id,
            platform="matrix",
            sender_id=sender,
            chat_id=room_id,
            text=body,
            timestamp=timestamp,
            reply_to=reply_to,
            raw=event,
        )
        self._message_queue.put_nowait(inbound)
