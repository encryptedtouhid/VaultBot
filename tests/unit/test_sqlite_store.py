"""Tests for SQLite persistent memory store."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vaultbot.memory.base import ConversationTurn, UserPreferences
from vaultbot.memory.sqlite_store import SQLiteMemoryStore


@pytest.fixture
async def store() -> SQLiteMemoryStore:
    """Create a temporary SQLite store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        s = SQLiteMemoryStore(db_path=db_path)
        yield s  # type: ignore[misc]
        await s.close()


@pytest.mark.asyncio
async def test_save_and_retrieve_turn(store: SQLiteMemoryStore) -> None:
    turn = ConversationTurn(
        chat_id="chat1",
        user_message="Hello",
        assistant_response="Hi there!",
        timestamp=datetime.now(UTC),
    )
    await store.save_turn(turn)
    history = await store.get_history("chat1")
    assert len(history) == 1
    assert history[0].user_message == "Hello"
    assert history[0].assistant_response == "Hi there!"


@pytest.mark.asyncio
async def test_history_respects_limit(store: SQLiteMemoryStore) -> None:
    for i in range(10):
        await store.save_turn(
            ConversationTurn(
                chat_id="chat1",
                user_message=f"msg{i}",
                assistant_response=f"resp{i}",
                timestamp=datetime.now(UTC),
            )
        )
    history = await store.get_history("chat1", limit=3)
    assert len(history) == 3
    # Should be the most recent 3, in chronological order
    assert history[0].user_message == "msg7"
    assert history[2].user_message == "msg9"


@pytest.mark.asyncio
async def test_history_per_chat_isolation(store: SQLiteMemoryStore) -> None:
    await store.save_turn(
        ConversationTurn(
            chat_id="chat1",
            user_message="hello",
            assistant_response="hi",
            timestamp=datetime.now(UTC),
        )
    )
    await store.save_turn(
        ConversationTurn(
            chat_id="chat2",
            user_message="hey",
            assistant_response="howdy",
            timestamp=datetime.now(UTC),
        )
    )
    h1 = await store.get_history("chat1")
    h2 = await store.get_history("chat2")
    assert len(h1) == 1
    assert len(h2) == 1
    assert h1[0].user_message == "hello"
    assert h2[0].user_message == "hey"


@pytest.mark.asyncio
async def test_save_and_get_summary(store: SQLiteMemoryStore) -> None:
    await store.save_summary("chat1", "User asked about weather")
    summary = await store.get_summary("chat1")
    assert summary == "User asked about weather"


@pytest.mark.asyncio
async def test_summary_upsert(store: SQLiteMemoryStore) -> None:
    await store.save_summary("chat1", "Old summary")
    await store.save_summary("chat1", "New summary")
    summary = await store.get_summary("chat1")
    assert summary == "New summary"


@pytest.mark.asyncio
async def test_get_nonexistent_summary(store: SQLiteMemoryStore) -> None:
    summary = await store.get_summary("nonexistent")
    assert summary is None


@pytest.mark.asyncio
async def test_save_and_get_user_preferences(store: SQLiteMemoryStore) -> None:
    prefs = UserPreferences(
        user_id="user1",
        platform="telegram",
        preferences={"language": "en", "notifications": True},
    )
    await store.save_user_preferences(prefs)
    result = await store.get_user_preferences("user1", "telegram")
    assert result is not None
    assert result.preferences["language"] == "en"
    assert result.preferences["notifications"] is True


@pytest.mark.asyncio
async def test_get_nonexistent_preferences(store: SQLiteMemoryStore) -> None:
    result = await store.get_user_preferences("nobody", "telegram")
    assert result is None
