"""Vector memory store with semantic search.

Stores conversation facts and memories as embeddings for semantic
retrieval.  Uses a simple in-memory vector index with cosine similarity
(can be upgraded to LanceDB for persistence).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry with text and embedding."""

    id: str
    text: str
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    importance: float = 1.0


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def simple_text_embedding(text: str, dim: int = 64) -> list[float]:
    """Generate a simple deterministic embedding from text.

    This is a placeholder for real embeddings (OpenAI, Cohere, etc.).
    Uses character-level hashing to produce a fixed-dim vector.
    """
    h = hashlib.sha256(text.lower().encode("utf-8")).hexdigest()
    # Convert hex to floats
    values = []
    for i in range(0, min(len(h), dim * 2), 2):
        values.append((int(h[i : i + 2], 16) - 128) / 128.0)
    # Pad or truncate
    while len(values) < dim:
        values.append(0.0)
    return values[:dim]


class VectorMemoryStore:
    """In-memory vector store for semantic memory search.

    Parameters
    ----------
    embedding_dim:
        Dimensionality of embedding vectors.
    max_entries:
        Maximum number of entries to store (oldest evicted first).
    """

    def __init__(
        self,
        embedding_dim: int = 64,
        max_entries: int = 10000,
    ) -> None:
        self._entries: dict[str, MemoryEntry] = {}
        self._dim = embedding_dim
        self._max_entries = max_entries
        self._counter: int = 0

    def add(
        self,
        text: str,
        *,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        importance: float = 1.0,
    ) -> MemoryEntry:
        """Add a memory entry with optional pre-computed embedding."""
        self._counter += 1
        entry_id = f"mem_{self._counter}"

        if embedding is None:
            embedding = simple_text_embedding(text, self._dim)

        entry = MemoryEntry(
            id=entry_id,
            text=text,
            embedding=embedding,
            metadata=metadata or {},
            importance=importance,
        )
        self._entries[entry_id] = entry

        # Evict oldest if over limit
        if len(self._entries) > self._max_entries:
            oldest_id = min(self._entries, key=lambda k: self._entries[k].created_at)
            del self._entries[oldest_id]

        logger.debug("vector_memory_added", entry_id=entry_id, text_len=len(text))
        return entry

    def search(
        self,
        query: str,
        *,
        query_embedding: list[float] | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[MemoryEntry, float]]:
        """Search for similar memories using cosine similarity.

        Returns
        -------
        list[tuple[MemoryEntry, float]]
            List of (entry, score) tuples sorted by descending similarity.
        """
        if query_embedding is None:
            query_embedding = simple_text_embedding(query, self._dim)

        scored: list[tuple[MemoryEntry, float]] = []
        for entry in self._entries.values():
            score = cosine_similarity(query_embedding, entry.embedding)
            # Weight by importance
            weighted_score = score * entry.importance
            if weighted_score >= min_score:
                scored.append((entry, weighted_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Get a memory entry by ID."""
        return self._entries.get(entry_id)

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def list_all(self, limit: int = 100) -> list[MemoryEntry]:
        """List all entries, newest first."""
        entries = sorted(
            self._entries.values(),
            key=lambda e: e.created_at,
            reverse=True,
        )
        return entries[:limit]

    @property
    def count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        """Remove all entries."""
        self._entries.clear()
