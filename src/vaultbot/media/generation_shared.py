"""Shared media generation infrastructure with fallback orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class NormalizationMeta:
    """Tracks requested vs applied parameter values."""

    requested: dict[str, object] = field(default_factory=dict)
    applied: dict[str, object] = field(default_factory=dict)
    normalized: bool = False


@dataclass(frozen=True, slots=True)
class GenerationCandidate:
    provider: str
    model: str = ""
    capabilities: list[str] = field(default_factory=list)
    priority: int = 0


class FallbackOrchestrator:
    """Orchestrates generation attempts across providers with fallback."""

    def __init__(self) -> None:
        self._candidates: list[GenerationCandidate] = []
        self._attempt_count = 0

    def add_candidate(self, candidate: GenerationCandidate) -> None:
        self._candidates.append(candidate)
        self._candidates.sort(key=lambda c: c.priority, reverse=True)

    def get_candidates(self, capability: str = "") -> list[GenerationCandidate]:
        if not capability:
            return list(self._candidates)
        return [c for c in self._candidates if capability in c.capabilities]

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    def next_candidate(self) -> GenerationCandidate | None:
        if self._attempt_count >= len(self._candidates):
            return None
        candidate = self._candidates[self._attempt_count]
        self._attempt_count += 1
        return candidate

    def reset(self) -> None:
        self._attempt_count = 0


def normalize_params(
    requested: dict[str, object], supported: dict[str, list[object]]
) -> NormalizationMeta:
    """Normalize requested params against supported values."""
    applied: dict[str, object] = {}
    for key, value in requested.items():
        options = supported.get(key, [])
        if not options or value in options:
            applied[key] = value
        else:
            applied[key] = options[0]  # Fall back to first supported value
    return NormalizationMeta(requested=requested, applied=applied, normalized=applied != requested)
