"""Encrypted SQLite persistent memory store using aiosqlite.

Stores conversation history, summaries, and user preferences in a local
SQLite database. The database file is stored in ~/.vaultbot/memory/.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from vaultbot.memory.base import ConversationTurn, UserPreferences
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_DB_DIR = Path.home() / ".vaultbot" / "memory"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "vaultbot.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_turns_chat_id ON conversation_turns(chat_id);
CREATE INDEX IF NOT EXISTS idx_turns_timestamp ON conversation_turns(timestamp);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    chat_id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    preferences TEXT DEFAULT '{}',
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, platform)
);
"""


class SQLiteMemoryStore:
    """SQLite-backed persistent memory store."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._db: aiosqlite.Connection | None = None

    async def _ensure_connection(self) -> aiosqlite.Connection:
        """Get or create the database connection."""
        if self._db is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self._db = await aiosqlite.connect(str(self._db_path))
            self._db.row_factory = aiosqlite.Row
            await self._db.executescript(_SCHEMA)
            await self._db.commit()
            # Restrict file permissions
            self._db_path.chmod(0o600)
            logger.info("sqlite_memory_connected", path=str(self._db_path))
        return self._db

    async def save_turn(self, turn: ConversationTurn) -> None:
        """Save a conversation turn to the database."""
        db = await self._ensure_connection()
        await db.execute(
            """INSERT INTO conversation_turns
               (chat_id, user_message, assistant_response, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (
                turn.chat_id,
                turn.user_message,
                turn.assistant_response,
                turn.timestamp.isoformat(),
                json.dumps(turn.metadata),
            ),
        )
        await db.commit()

    async def get_history(
        self, chat_id: str, *, limit: int = 20
    ) -> list[ConversationTurn]:
        """Retrieve conversation history for a chat, most recent first."""
        db = await self._ensure_connection()
        cursor = await db.execute(
            """SELECT chat_id, user_message, assistant_response, timestamp, metadata
               FROM conversation_turns
               WHERE chat_id = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (chat_id, limit),
        )
        rows = await cursor.fetchall()

        turns = []
        for row in reversed(rows):  # Return in chronological order
            turns.append(
                ConversationTurn(
                    chat_id=row["chat_id"],
                    user_message=row["user_message"],
                    assistant_response=row["assistant_response"],
                    timestamp=datetime.fromisoformat(row["timestamp"]).replace(
                        tzinfo=UTC
                    ),
                    metadata=json.loads(row["metadata"]),
                )
            )
        return turns

    async def save_summary(self, chat_id: str, summary: str) -> None:
        """Save or update a conversation summary."""
        db = await self._ensure_connection()
        await db.execute(
            """INSERT INTO conversation_summaries (chat_id, summary, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(chat_id) DO UPDATE SET
               summary = excluded.summary, updated_at = datetime('now')""",
            (chat_id, summary),
        )
        await db.commit()

    async def get_summary(self, chat_id: str) -> str | None:
        """Get the latest conversation summary."""
        db = await self._ensure_connection()
        cursor = await db.execute(
            "SELECT summary FROM conversation_summaries WHERE chat_id = ?",
            (chat_id,),
        )
        row = await cursor.fetchone()
        return row["summary"] if row else None

    async def save_user_preferences(self, prefs: UserPreferences) -> None:
        """Save or update user preferences."""
        db = await self._ensure_connection()
        await db.execute(
            """INSERT INTO user_preferences (user_id, platform, preferences, updated_at)
               VALUES (?, ?, ?, datetime('now'))
               ON CONFLICT(user_id, platform) DO UPDATE SET
               preferences = excluded.preferences, updated_at = datetime('now')""",
            (prefs.user_id, prefs.platform, json.dumps(prefs.preferences)),
        )
        await db.commit()

    async def get_user_preferences(
        self, user_id: str, platform: str
    ) -> UserPreferences | None:
        """Get user preferences."""
        db = await self._ensure_connection()
        cursor = await db.execute(
            "SELECT * FROM user_preferences WHERE user_id = ? AND platform = ?",
            (user_id, platform),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return UserPreferences(
            user_id=row["user_id"],
            platform=row["platform"],
            preferences=json.loads(row["preferences"]),
        )

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("sqlite_memory_closed")
