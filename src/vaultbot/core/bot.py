"""Main VaultBot orchestrator — ties platforms, LLM, security, and routing together."""

from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING

from vaultbot.core.context import ContextManager
from vaultbot.core.router import MessageRouter
from vaultbot.security.audit import AuditLogger
from vaultbot.security.auth import AuthManager
from vaultbot.security.rate_limiter import RateLimiter
from vaultbot.utils.logging import get_logger

if TYPE_CHECKING:
    from vaultbot.config import VaultBotConfig
    from vaultbot.llm.base import LLMProvider
    from vaultbot.platforms.base import PlatformAdapter

logger = get_logger(__name__)


class VaultBot:
    """Main bot orchestrator."""

    def __init__(self, config: VaultBotConfig) -> None:
        self._config = config
        self._platforms: dict[str, PlatformAdapter] = {}
        self._llm: LLMProvider | None = None
        self._running = False

        # Security components
        self._auth = AuthManager(config.get_allowlist())
        self._rate_limiter = RateLimiter(
            user_capacity=config.rate_limit.user_capacity,
            user_refill_rate=config.rate_limit.user_refill_rate,
            global_capacity=config.rate_limit.global_capacity,
            global_refill_rate=config.rate_limit.global_refill_rate,
        )
        self._audit = AuditLogger()
        self._context_manager = ContextManager(
            system_prompt=config.system_prompt,
            max_history=config.max_history,
        )
        self._router: MessageRouter | None = None

    def register_platform(self, adapter: PlatformAdapter) -> None:
        """Register a messaging platform adapter."""
        self._platforms[adapter.platform_name] = adapter
        logger.info("platform_registered", platform=adapter.platform_name)

    def set_llm(self, llm: LLMProvider) -> None:
        """Set the LLM provider."""
        self._llm = llm
        logger.info("llm_registered", provider=llm.provider_name)

    async def _listen_platform(self, adapter: PlatformAdapter) -> None:
        """Listen for messages on a single platform."""
        assert self._router is not None
        logger.info("listening", platform=adapter.platform_name)

        async for message in adapter.listen():
            try:
                await self._router.handle(message, adapter)
            except Exception as e:
                logger.error(
                    "message_handling_error",
                    platform=adapter.platform_name,
                    error=str(e),
                )
                self._audit.log_error(
                    error=str(e),
                    platform=adapter.platform_name,
                )

    async def start(self) -> None:
        """Start the bot and listen on all registered platforms."""
        if not self._platforms:
            raise RuntimeError("No platforms registered. Add at least one platform adapter.")
        if self._llm is None:
            raise RuntimeError("No LLM provider set. Call set_llm() first.")

        self._router = MessageRouter(
            auth=self._auth,
            rate_limiter=self._rate_limiter,
            audit=self._audit,
            context_manager=self._context_manager,
            llm=self._llm,
        )

        self._running = True
        logger.info(
            "zenbot_starting",
            platforms=list(self._platforms.keys()),
            llm=self._llm.provider_name,
        )

        # Connect all platforms
        for adapter in self._platforms.values():
            try:
                await adapter.connect()
            except Exception as e:
                logger.error(
                    "platform_connect_failed",
                    platform=adapter.platform_name,
                    error=str(e),
                )
                raise

        # Set up graceful shutdown (Unix only — Windows uses KeyboardInterrupt)
        import sys

        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # Listen on all platforms concurrently
        tasks = [
            asyncio.create_task(self._listen_platform(adapter))
            for adapter in self._platforms.values()
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("zenbot_shutting_down")

    async def stop(self) -> None:
        """Gracefully stop the bot."""
        if not self._running:
            return
        self._running = False
        logger.info("zenbot_stopping")

        for adapter in self._platforms.values():
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.error("disconnect_error", platform=adapter.platform_name, error=str(e))

        # Cancel all running tasks
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
