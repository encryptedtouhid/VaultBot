"""Microsoft Teams messaging platform adapter.

Uses the Bot Framework SDK for Python to communicate with Teams via
Azure Bot Service. Supports both polling (via Bot Framework Emulator
for dev) and webhook mode (for production).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

try:
    from botbuilder.core import (
        BotFrameworkAdapter,
        BotFrameworkAdapterSettings,
        TurnContext,
    )
    from botbuilder.schema import Activity, ActivityTypes

    _TEAMS_AVAILABLE = True
except ImportError:
    _TEAMS_AVAILABLE = False

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class TeamsAdapter:
    """Microsoft Teams bot adapter using Bot Framework SDK.

    Requires:
        - Microsoft App ID (from Azure Bot registration)
        - Microsoft App Password
    """

    def __init__(
        self,
        *,
        app_id: str,
        app_password: str,
    ) -> None:
        if not _TEAMS_AVAILABLE:
            raise ImportError(
                "Teams support requires 'botbuilder-core'. "
                "Install with: pip install botbuilder-core"
            )
        self._app_id = app_id
        self._app_password = app_password
        self._message_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._adapter = BotFrameworkAdapter(
            BotFrameworkAdapterSettings(app_id, app_password)
        )
        # Store conversation references for sending proactive messages
        self._conversation_refs: dict[str, object] = {}

    @property
    def platform_name(self) -> str:
        return "teams"

    async def connect(self) -> None:
        """Initialize the Teams adapter."""
        logger.info("teams_connected", app_id=self._app_id)

    async def disconnect(self) -> None:
        """Disconnect the Teams adapter."""
        logger.info("teams_disconnected")

    async def process_activity(self, activity_json: dict) -> None:  # type: ignore[type-arg]
        """Process an incoming activity from the Bot Framework webhook.

        Call this from your webhook endpoint handler.
        """
        activity = Activity().deserialize(activity_json)

        async def on_turn(turn_context: TurnContext) -> None:
            if turn_context.activity.type == ActivityTypes.message:
                text = turn_context.activity.text or ""
                sender = turn_context.activity.from_property
                conversation = turn_context.activity.conversation

                # Store conversation reference for proactive messaging
                ref = TurnContext.get_conversation_reference(turn_context.activity)
                conv_id = conversation.id if conversation else "unknown"
                self._conversation_refs[conv_id] = ref

                inbound = InboundMessage(
                    id=turn_context.activity.id or "",
                    platform="teams",
                    sender_id=sender.id if sender else "unknown",
                    chat_id=conv_id,
                    text=text,
                    timestamp=turn_context.activity.timestamp.replace(tzinfo=UTC)
                    if turn_context.activity.timestamp
                    else datetime.now(UTC),
                    reply_to=turn_context.activity.reply_to_id,
                    raw=turn_context.activity,
                )
                await self._message_queue.put(inbound)

        await self._adapter.process_activity(activity, "", on_turn)

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield messages as they arrive from Teams."""
        while True:
            message = await self._message_queue.get()
            yield message

    async def send(self, message: OutboundMessage) -> None:
        """Send a message to a Teams conversation."""
        ref = self._conversation_refs.get(message.chat_id)
        if ref is None:
            logger.error("teams_no_conversation_ref", chat_id=message.chat_id)
            return

        async def send_callback(turn_context: TurnContext) -> None:
            await turn_context.send_activity(message.text)

        await self._adapter.continue_conversation(
            ref,  # type: ignore[arg-type]
            send_callback,
            self._app_id,
        )

    async def healthcheck(self) -> bool:
        """Check if the Teams adapter is initialized."""
        return self._adapter is not None
