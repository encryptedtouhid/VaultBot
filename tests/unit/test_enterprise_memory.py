"""Unit tests for enterprise memory system."""

from __future__ import annotations

import pytest

from vaultbot.memory.dreaming_pipeline import DreamingPipeline, DreamPhase
from vaultbot.memory.embeddings import EmbeddingEngine, EmbeddingProvider, EmbeddingResult
from vaultbot.memory.semantic_search import (
    SearchDocument,
    SemanticSearchEngine,
    cosine_similarity,
)

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------


class MockEmbeddingProvider:
    @property
    def provider_name(self) -> str:
        return "mock"

    async def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.1, 0.2, 0.3], model="mock", dimensions=3)

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        return [await self.embed(t) for t in texts]


class TestEmbeddingEngine:
    def test_mock_is_provider(self) -> None:
        assert isinstance(MockEmbeddingProvider(), EmbeddingProvider)

    @pytest.mark.asyncio
    async def test_embed(self) -> None:
        engine = EmbeddingEngine()
        engine.register(MockEmbeddingProvider())
        result = await engine.embed("hello")
        assert len(result.vector) == 3
        assert engine.embed_count == 1

    @pytest.mark.asyncio
    async def test_embed_batch(self) -> None:
        engine = EmbeddingEngine()
        engine.register(MockEmbeddingProvider())
        results = await engine.embed_batch(["a", "b", "c"])
        assert len(results) == 3
        assert engine.embed_count == 3

    @pytest.mark.asyncio
    async def test_unknown_provider(self) -> None:
        engine = EmbeddingEngine()
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            await engine.embed("hello")


# ---------------------------------------------------------------------------
# Semantic Search
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical(self) -> None:
        assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal(self) -> None:
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_empty(self) -> None:
        assert cosine_similarity([], []) == 0.0

    def test_different_lengths(self) -> None:
        assert cosine_similarity([1], [1, 2]) == 0.0


class TestSemanticSearchEngine:
    def test_add_and_search(self) -> None:
        engine = SemanticSearchEngine()
        engine.add_document(SearchDocument(doc_id="d1", content="hello", vector=[1.0, 0.0, 0.0]))
        engine.add_document(SearchDocument(doc_id="d2", content="world", vector=[0.0, 1.0, 0.0]))
        results = engine.search([1.0, 0.0, 0.0], limit=1)
        assert len(results) == 1
        assert results[0].doc_id == "d1"

    def test_collection_filter(self) -> None:
        engine = SemanticSearchEngine()
        engine.add_document(
            SearchDocument(doc_id="d1", content="a", vector=[1, 0], collection="work")
        )
        engine.add_document(
            SearchDocument(doc_id="d2", content="b", vector=[1, 0], collection="personal")
        )
        results = engine.search([1, 0], collection="work")
        assert len(results) == 1

    def test_min_score(self) -> None:
        engine = SemanticSearchEngine()
        engine.add_document(SearchDocument(doc_id="d1", content="a", vector=[1, 0]))
        results = engine.search([0, 1], min_score=0.5)
        assert len(results) == 0

    def test_remove_document(self) -> None:
        engine = SemanticSearchEngine()
        engine.add_document(SearchDocument(doc_id="d1", content="a"))
        assert engine.remove_document("d1") is True
        assert engine.document_count == 0

    def test_list_collections(self) -> None:
        engine = SemanticSearchEngine()
        engine.add_document(SearchDocument(doc_id="d1", content="a", collection="a"))
        engine.add_document(SearchDocument(doc_id="d2", content="b", collection="b"))
        assert set(engine.list_collections()) == {"a", "b"}


# ---------------------------------------------------------------------------
# Dreaming Pipeline
# ---------------------------------------------------------------------------


class TestDreamingPipeline:
    @pytest.mark.asyncio
    async def test_light_phase(self) -> None:
        pipeline = DreamingPipeline()
        entries = [{"content": "hello"}, {"content": "hello"}, {"content": "world"}]
        result = await pipeline.run_light(entries)
        assert result.phase == DreamPhase.LIGHT
        assert result.deduped == 1

    @pytest.mark.asyncio
    async def test_deep_phase(self) -> None:
        pipeline = DreamingPipeline()
        entries = [
            {"content": "a", "tags": ["python"]},
            {"content": "b", "tags": ["python"]},
            {"content": "c", "tags": ["rust"]},
        ]
        result = await pipeline.run_deep(entries)
        assert result.phase == DreamPhase.DEEP
        assert result.patterns_found >= 1

    @pytest.mark.asyncio
    async def test_rem_phase(self) -> None:
        pipeline = DreamingPipeline()
        result = await pipeline.run_rem([{"content": str(i)} for i in range(100)])
        assert result.phase == DreamPhase.REM
        assert result.consolidated == 10

    def test_phase_due(self) -> None:
        pipeline = DreamingPipeline()
        assert pipeline.is_phase_due(DreamPhase.LIGHT) is True
        due = pipeline.get_due_phases()
        assert DreamPhase.LIGHT in due

    @pytest.mark.asyncio
    async def test_total_runs(self) -> None:
        pipeline = DreamingPipeline()
        await pipeline.run_light([])
        await pipeline.run_deep([])
        assert pipeline.total_runs == 2
