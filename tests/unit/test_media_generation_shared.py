"""Unit tests for media generation shared infrastructure."""

from __future__ import annotations

from vaultbot.media.generation_shared import (
    FallbackOrchestrator,
    GenerationCandidate,
    normalize_params,
)


class TestFallbackOrchestrator:
    def test_add_candidate(self) -> None:
        orch = FallbackOrchestrator()
        orch.add_candidate(GenerationCandidate(provider="dalle", priority=10))
        assert orch.candidate_count == 1

    def test_priority_ordering(self) -> None:
        orch = FallbackOrchestrator()
        orch.add_candidate(GenerationCandidate(provider="low", priority=1))
        orch.add_candidate(GenerationCandidate(provider="high", priority=10))
        candidates = orch.get_candidates()
        assert candidates[0].provider == "high"

    def test_filter_by_capability(self) -> None:
        orch = FallbackOrchestrator()
        orch.add_candidate(GenerationCandidate(provider="a", capabilities=["image"]))
        orch.add_candidate(GenerationCandidate(provider="b", capabilities=["video"]))
        assert len(orch.get_candidates("image")) == 1

    def test_next_candidate(self) -> None:
        orch = FallbackOrchestrator()
        orch.add_candidate(GenerationCandidate(provider="a", priority=10))
        orch.add_candidate(GenerationCandidate(provider="b", priority=5))
        assert orch.next_candidate().provider == "a"
        assert orch.next_candidate().provider == "b"
        assert orch.next_candidate() is None

    def test_reset(self) -> None:
        orch = FallbackOrchestrator()
        orch.add_candidate(GenerationCandidate(provider="a"))
        orch.next_candidate()
        orch.reset()
        assert orch.next_candidate() is not None


class TestNormalization:
    def test_no_normalization_needed(self) -> None:
        meta = normalize_params({"size": "1024x1024"}, {"size": ["1024x1024", "512x512"]})
        assert meta.normalized is False
        assert meta.applied["size"] == "1024x1024"

    def test_normalization_applied(self) -> None:
        meta = normalize_params({"size": "2048x2048"}, {"size": ["1024x1024", "512x512"]})
        assert meta.normalized is True
        assert meta.applied["size"] == "1024x1024"

    def test_unsupported_key(self) -> None:
        meta = normalize_params({"quality": "hd"}, {})
        assert meta.applied["quality"] == "hd"
