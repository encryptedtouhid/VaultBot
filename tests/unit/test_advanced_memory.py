"""Unit tests for advanced memory systems."""

from __future__ import annotations

import pytest

from vaultbot.memory.active_memory import ActiveMemoryStore
from vaultbot.memory.dreaming import MemoryDreamer
from vaultbot.memory.wiki import WikiKnowledgeBase


class TestWikiKnowledgeBase:
    def test_create_page(self) -> None:
        wiki = WikiKnowledgeBase()
        page = wiki.create_page("Test", "Content", tags=["tag1"])
        assert page.title == "Test"
        assert wiki.page_count == 1

    def test_create_duplicate_raises(self) -> None:
        wiki = WikiKnowledgeBase()
        wiki.create_page("Test", "Content")
        with pytest.raises(ValueError, match="already exists"):
            wiki.create_page("Test", "Other")

    def test_get_page(self) -> None:
        wiki = WikiKnowledgeBase()
        wiki.create_page("Test", "Content")
        assert wiki.get_page("Test") is not None
        assert wiki.get_page("Missing") is None

    def test_update_page(self) -> None:
        wiki = WikiKnowledgeBase()
        wiki.create_page("Test", "v1")
        page = wiki.update_page("Test", "v2")
        assert page.content == "v2"
        assert page.version == 2

    def test_update_missing_raises(self) -> None:
        wiki = WikiKnowledgeBase()
        with pytest.raises(KeyError):
            wiki.update_page("Missing", "content")

    def test_delete_page(self) -> None:
        wiki = WikiKnowledgeBase()
        wiki.create_page("Test", "Content")
        assert wiki.delete_page("Test") is True
        assert wiki.page_count == 0

    def test_search(self) -> None:
        wiki = WikiKnowledgeBase()
        wiki.create_page("Python", "A programming language")
        wiki.create_page("Java", "Another language")
        results = wiki.search("python")
        assert len(results) == 1

    def test_list_pages(self) -> None:
        wiki = WikiKnowledgeBase()
        wiki.create_page("A", "content")
        wiki.create_page("B", "content")
        assert set(wiki.list_pages()) == {"A", "B"}


class TestActiveMemoryStore:
    def test_store_and_recall(self) -> None:
        store = ActiveMemoryStore()
        store.store("key1", "hello", tags=["greeting"])
        entry = store.recall("key1")
        assert entry is not None
        assert entry.content == "hello"
        assert entry.access_count == 1

    def test_recall_missing(self) -> None:
        store = ActiveMemoryStore()
        assert store.recall("missing") is None

    def test_search_by_relevance(self) -> None:
        store = ActiveMemoryStore()
        store.store("py", "python programming", tags=["code"])
        store.store("js", "javascript web", tags=["code"])
        results = store.search_by_relevance("python")
        assert len(results) == 1
        assert results[0].key == "py"

    def test_forget(self) -> None:
        store = ActiveMemoryStore()
        store.store("key1", "data")
        assert store.forget("key1") is True
        assert store.entry_count == 0

    def test_eviction(self) -> None:
        store = ActiveMemoryStore(max_entries=2)
        store.store("a", "data1")
        store.store("b", "data2")
        store.store("c", "data3")
        assert store.entry_count == 2


class TestMemoryDreamer:
    @pytest.mark.asyncio
    async def test_dream_empty(self) -> None:
        dreamer = MemoryDreamer()
        result = await dreamer.dream([])
        assert result.merged_count == 0
        assert result.pruned_count == 0
        assert dreamer.dream_count == 1

    @pytest.mark.asyncio
    async def test_dream_with_stale(self) -> None:
        dreamer = MemoryDreamer(stale_threshold_seconds=0)
        entries = [{"key": "old", "last_accessed": 0.0, "tags": []}]
        result = await dreamer.dream(entries)
        assert result.pruned_count == 1

    @pytest.mark.asyncio
    async def test_dream_detects_clusters(self) -> None:
        dreamer = MemoryDreamer()
        entries = [
            {"key": "a", "tags": ["python"], "last_accessed": 9999999999.0},
            {"key": "b", "tags": ["python"], "last_accessed": 9999999999.0},
        ]
        result = await dreamer.dream(entries)
        assert result.merged_count >= 1
        assert len(result.insights) >= 1
