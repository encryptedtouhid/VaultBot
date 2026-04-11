"""Message router — directs incoming messages to the appropriate handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vaultbot.core.message import ChatMessage, InboundMessage, OutboundMessage
from vaultbot.security.audit import AuditLogger, EventType
from vaultbot.security.auth import AuthManager
from vaultbot.security.rate_limiter import RateLimiter
from vaultbot.utils.logging import get_logger

if TYPE_CHECKING:
    from vaultbot.core.context import ContextManager
    from vaultbot.llm.base import LLMProvider
    from vaultbot.platforms.base import PlatformAdapter

logger = get_logger(__name__)


class MessageRouter:
    """Routes inbound messages through auth, rate limiting, LLM, and response."""

    def __init__(
        self,
        *,
        auth: AuthManager,
        rate_limiter: RateLimiter,
        audit: AuditLogger,
        context_manager: ContextManager,
        llm: LLMProvider,
    ) -> None:
        self._auth = auth
        self._rate_limiter = rate_limiter
        self._audit = audit
        self._context_manager = context_manager
        self._llm = llm

    async def handle(
        self, message: InboundMessage, adapter: PlatformAdapter
    ) -> None:
        """Process an inbound message through the full pipeline."""
        # 1. Authenticate
        if not self._auth.is_authorized(message.platform, message.sender_id):
            self._audit.log_auth(
                platform=message.platform,
                user_id=message.sender_id,
                success=False,
                reason="not_in_allowlist",
            )
            await adapter.send(
                OutboundMessage(
                    chat_id=message.chat_id,
                    text="You are not authorized to use this bot. "
                    "Contact the bot admin to be added to the allowlist.",
                    reply_to=message.id,
                )
            )
            return

        self._audit.log_auth(
            platform=message.platform,
            user_id=message.sender_id,
            success=True,
        )

        # 2. Rate limit
        qualified_id = f"{message.platform}:{message.sender_id}"
        if not self._rate_limiter.is_allowed(qualified_id):
            wait_time = self._rate_limiter.time_until_allowed(qualified_id)
            await adapter.send(
                OutboundMessage(
                    chat_id=message.chat_id,
                    text=f"Rate limited. Please wait {wait_time:.0f}s.",
                    reply_to=message.id,
                )
            )
            return

        # 3. Build conversation context and call LLM
        context = self._context_manager.get(message.chat_id)
        context.add_message(ChatMessage(role="user", content=message.text))

        try:
            response = await self._llm.complete(context.get_messages())
            assistant_text = response.content

            context.add_message(ChatMessage(role="assistant", content=assistant_text))

            self._audit.log_action(
                event_type=EventType.MESSAGE_SENT,
                platform=message.platform,
                user_id=message.sender_id,
            )

            await adapter.send(
                OutboundMessage(
                    chat_id=message.chat_id,
                    text=assistant_text,
                    reply_to=message.id,
                )
            )

        except Exception as e:
            logger.error("llm_error", error=str(e))
            self._audit.log_error(
                error=str(e),
                platform=message.platform,
                user_id=message.sender_id,
            )
            await adapter.send(
                OutboundMessage(
                    chat_id=message.chat_id,
                    text="An error occurred while processing your request. Please try again.",
                    reply_to=message.id,
                )
            )
