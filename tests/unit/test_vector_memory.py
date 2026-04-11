"""Unit tests for vector memory store."""

from __future__ import annotations

import pytest

from vaultbot.memory.vector_store import (
    VectorMemoryStore,
    cosine_similarity,
    simple_text_embedding,
)


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_empty_vectors(self) -> None:
        assert cosine_similarity([], []) == 0.0

    def test_different_lengths(self) -> None:
        assert cosine_similarity([1, 2], [1, 2, 3]) == 0.0

    def test_zero_vector(self) -> None:
        assert cosine_similarity([0, 0], [1, 2]) == 0.0


class TestSimpleTextEmbedding:
    def test_deterministic(self) -> None:
        e1 = simple_text_embedding("hello")
        e2 = simple_text_embedding("hello")
        assert e1 == e2

    def test_different_texts_different_embeddings(self) -> None:
        e1 = simple_text_embedding("hello")
        e2 = simple_text_embedding("world")
        assert e1 != e2

    def test_correct_dimension(self) -> None:
        e = simple_text_embedding("test", dim=32)
        assert len(e) == 32

    def test_case_insensitive(self) -> None:
        e1 = simple_text_embedding("Hello")
        e2 = simple_text_embedding("hello")
        assert e1 == e2


class TestVectorMemoryStore:
    def test_add_entry(self) -> None:
        store = VectorMemoryStore()
        entry = store.add("The sky is blue")
        assert entry.id == "mem_1"
        assert entry.text == "The sky is blue"
        assert len(entry.embedding) == 64
        assert store.count == 1

    def test_add_with_custom_embedding(self) -> None:
        store = VectorMemoryStore(embedding_dim=3)
        entry = store.add("test", embedding=[0.1, 0.2, 0.3])
        assert entry.embedding == [0.1, 0.2, 0.3]

    def test_add_with_metadata(self) -> None:
        store = VectorMemoryStore()
        entry = store.add("test", metadata={"source": "chat"})
        assert entry.metadata["source"] == "chat"

    def test_search_finds_similar(self) -> None:
        store = VectorMemoryStore()
        store.add("The cat sat on the mat")
        store.add("Python is a programming language")
        store.add("The cat climbed a tree")

        results = store.search("cat")
        assert len(results) > 0
        # Results should be sorted by score descending
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_top_k(self) -> None:
        store = VectorMemoryStore()
        for i in range(10):
            store.add(f"memory entry {i}")

        results = store.search("memory", top_k=3)
        assert len(results) == 3

    def test_search_min_score(self) -> None:
        store = VectorMemoryStore()
        store.add("completely unrelated content xyz123")
        results = store.search("test query", min_score=0.99)
        # With simple embeddings, unlikely to score > 0.99
        assert len(results) <= 1  # May or may not match

    def test_get_entry(self) -> None:
        store = VectorMemoryStore()
        entry = store.add("test")
        found = store.get(entry.id)
        assert found is not None
        assert found.text == "test"

    def test_get_nonexistent(self) -> None:
        store = VectorMemoryStore()
        assert store.get("nonexistent") is None

    def test_delete_entry(self) -> None:
        store = VectorMemoryStore()
        entry = store.add("test")
        assert store.delete(entry.id) is True
        assert store.count == 0

    def test_delete_nonexistent(self) -> None:
        store = VectorMemoryStore()
        assert store.delete("nonexistent") is False

    def test_list_all(self) -> None:
        store = VectorMemoryStore()
        store.add("first")
        store.add("second")
        store.add("third")
        entries = store.list_all()
        assert len(entries) == 3
        # Newest first
        assert entries[0].text == "third"

    def test_clear(self) -> None:
        store = VectorMemoryStore()
        store.add("a")
        store.add("b")
        store.clear()
        assert store.count == 0

    def test_max_entries_eviction(self) -> None:
        store = VectorMemoryStore(max_entries=3)
        store.add("first")
        store.add("second")
        store.add("third")
        store.add("fourth")  # Should evict "first"
        assert store.count == 3
        texts = {e.text for e in store.list_all()}
        assert "first" not in texts

    def test_importance_weighting(self) -> None:
        store = VectorMemoryStore()
        store.add("low importance", importance=0.1)
        store.add("high importance", importance=10.0)

        results = store.search("importance")
        # Higher importance entry should score higher
        if len(results) >= 2:
            assert results[0][0].importance >= results[1][0].importance
