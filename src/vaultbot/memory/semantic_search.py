"""Semantic search with collection management."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class SearchDocument:
    doc_id: str
    content: str
    vector: list[float] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    collection: str = "default"


@dataclass(frozen=True, slots=True)
class SearchResult:
    doc_id: str
    content: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class SemanticSearchEngine:
    """Semantic search over collections of embedded documents."""

    def __init__(self) -> None:
        self._documents: dict[str, SearchDocument] = {}

    @property
    def document_count(self) -> int:
        return len(self._documents)

    def add_document(self, doc: SearchDocument) -> None:
        self._documents[doc.doc_id] = doc

    def remove_document(self, doc_id: str) -> bool:
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False

    def search(
        self,
        query_vector: list[float],
        collection: str = "",
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search for similar documents using cosine similarity."""
        results: list[SearchResult] = []
        for doc in self._documents.values():
            if collection and doc.collection != collection:
                continue
            if not doc.vector:
                continue
            score = cosine_similarity(query_vector, doc.vector)
            if score >= min_score:
                results.append(
                    SearchResult(
                        doc_id=doc.doc_id,
                        content=doc.content,
                        score=score,
                        metadata=doc.metadata,
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def list_collections(self) -> list[str]:
        return list({d.collection for d in self._documents.values()})

    def collection_count(self, collection: str) -> int:
        return sum(1 for d in self._documents.values() if d.collection == collection)
