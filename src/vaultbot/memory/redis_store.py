"""Redis-backed persistent memory store for multi-instance deployments.

Uses Redis as the backend for conversation history, summaries, and user
preferences. This allows multiple VaultBot instances to share state.

Requires the `redis` optional dependency:
    pip install vaultbot-agent[redis]
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from vaultbot.memory.base import ConversationTurn, UserPreferences
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "zenbot:"


class RedisMemoryStore:
    """Redis-backed memory store for multi-instance deployments."""

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        key_prefix: str = _KEY_PREFIX,
    ) -> None:
        try:
            import redis.asyncio as aioredis
        except ImportError as e:
            raise ImportError(
                "Redis support requires the 'redis' package. "
                "Install with: pip install vaultbot-agent[redis]"
            ) from e

        self._client = aioredis.from_url(url, decode_responses=True)
        self._prefix = key_prefix

    def _key(self, *parts: str) -> str:
        """Build a namespaced Redis key."""
        return self._prefix + ":".join(parts)

    async def save_turn(self, turn: ConversationTurn) -> None:
        """Save a conversation turn to a Redis list."""
        key = self._key("turns", turn.chat_id)
        data = json.dumps({
            "chat_id": turn.chat_id,
            "user_message": turn.user_message,
            "assistant_response": turn.assistant_response,
            "timestamp": turn.timestamp.isoformat(),
            "metadata": turn.metadata,
        })
        await self._client.rpush(key, data)
        # Keep only last 1000 turns per chat to prevent unbounded growth
        await self._client.ltrim(key, -1000, -1)

    async def get_history(
        self, chat_id: str, *, limit: int = 20
    ) -> list[ConversationTurn]:
        """Retrieve conversation history from Redis."""
        key = self._key("turns", chat_id)
        # Get the last `limit` entries
        raw_entries = await self._client.lrange(key, -limit, -1)

        turns = []
        for raw in raw_entries:
            data = json.loads(raw)
            turns.append(
                ConversationTurn(
                    chat_id=data["chat_id"],
                    user_message=data["user_message"],
                    assistant_response=data["assistant_response"],
                    timestamp=datetime.fromisoformat(data["timestamp"]).replace(
                        tzinfo=UTC
                    ),
                    metadata=data.get("metadata", {}),
                )
            )
        return turns

    async def save_summary(self, chat_id: str, summary: str) -> None:
        """Save a conversation summary."""
        key = self._key("summary", chat_id)
        await self._client.set(key, summary)

    async def get_summary(self, chat_id: str) -> str | None:
        """Get the latest conversation summary."""
        key = self._key("summary", chat_id)
        return await self._client.get(key)

    async def save_user_preferences(self, prefs: UserPreferences) -> None:
        """Save user preferences."""
        key = self._key("prefs", prefs.platform, prefs.user_id)
        await self._client.set(key, json.dumps({
            "user_id": prefs.user_id,
            "platform": prefs.platform,
            "preferences": prefs.preferences,
        }))

    async def get_user_preferences(
        self, user_id: str, platform: str
    ) -> UserPreferences | None:
        """Get user preferences."""
        key = self._key("prefs", platform, user_id)
        raw = await self._client.get(key)
        if not raw:
            return None
        data = json.loads(raw)
        return UserPreferences(
            user_id=data["user_id"],
            platform=data["platform"],
            preferences=data.get("preferences", {}),
        )

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._client.aclose()
        logger.info("redis_memory_closed")
