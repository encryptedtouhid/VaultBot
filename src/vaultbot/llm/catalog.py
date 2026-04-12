"""Dynamic model catalog discovery from providers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ModelCapability(str, Enum):
    CHAT = "chat"
    VISION = "vision"
    TOOL_USE = "tool_use"
    THINKING = "thinking"
    CODE = "code"
    EMBEDDING = "embedding"


@dataclass(frozen=True, slots=True)
class ModelInfo:
    model_id: str
    provider: str
    display_name: str = ""
    context_window: int = 0
    max_output_tokens: int = 0
    capabilities: list[ModelCapability] = field(default_factory=list)
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    model: ModelInfo
    cached_at: float = field(default_factory=time.time)


class ModelCatalog:
    """Dynamic model catalog with caching and search."""

    def __init__(self, cache_ttl: float = 3600.0) -> None:
        self._entries: dict[str, CatalogEntry] = {}
        self._aliases: dict[str, str] = {}
        self._cache_ttl = cache_ttl

    @property
    def model_count(self) -> int:
        return len(self._entries)

    def register_model(self, model: ModelInfo) -> None:
        self._entries[model.model_id] = CatalogEntry(model=model)

    def register_alias(self, alias: str, model_id: str) -> None:
        self._aliases[alias] = model_id

    def resolve(self, name: str) -> ModelInfo | None:
        model_id = self._aliases.get(name, name)
        entry = self._entries.get(model_id)
        return entry.model if entry else None

    def search(self, query: str) -> list[ModelInfo]:
        q = query.lower()
        return [
            e.model
            for e in self._entries.values()
            if q in e.model.model_id.lower() or q in e.model.display_name.lower()
        ]

    def filter_by_capability(self, capability: ModelCapability) -> list[ModelInfo]:
        return [e.model for e in self._entries.values() if capability in e.model.capabilities]

    def filter_by_provider(self, provider: str) -> list[ModelInfo]:
        return [e.model for e in self._entries.values() if e.model.provider == provider]

    def list_all(self) -> list[ModelInfo]:
        return [e.model for e in self._entries.values()]

    def cheapest(self, capability: ModelCapability | None = None) -> ModelInfo | None:
        models = self.filter_by_capability(capability) if capability else self.list_all()
        priced = [m for m in models if m.input_cost_per_1k > 0]
        if not priced:
            return None
        return min(priced, key=lambda m: m.input_cost_per_1k)
