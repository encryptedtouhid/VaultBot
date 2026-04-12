"""Live model switching with fallback chains."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ModelOption:
    model_id: str
    provider: str = ""
    context_tokens: int = 8192
    priority: int = 0


@dataclass(slots=True)
class ModelSwitcherConfig:
    default_model: str = "claude-sonnet-4-20250514"
    fallback_chain: list[str] = field(default_factory=list)
    max_context_tokens: int = 128000


class ModelSwitcher:
    """Switch models mid-session with fallback support."""

    def __init__(self, config: ModelSwitcherConfig | None = None) -> None:
        self._config = config or ModelSwitcherConfig()
        self._current_model: str = self._config.default_model
        self._models: dict[str, ModelOption] = {}
        self._switch_count = 0

    @property
    def current_model(self) -> str:
        return self._current_model

    @property
    def switch_count(self) -> int:
        return self._switch_count

    def register_model(self, option: ModelOption) -> None:
        self._models[option.model_id] = option

    def switch(self, model_id: str) -> bool:
        if model_id in self._models or model_id == self._config.default_model:
            self._current_model = model_id
            self._switch_count += 1
            logger.info("model_switched", model=model_id)
            return True
        return False

    def fallback(self) -> str | None:
        """Switch to next model in fallback chain."""
        chain = self._config.fallback_chain
        if not chain:
            return None
        try:
            idx = chain.index(self._current_model)
            if idx + 1 < len(chain):
                next_model = chain[idx + 1]
                self._current_model = next_model
                self._switch_count += 1
                logger.info("model_fallback", model=next_model)
                return next_model
        except ValueError:
            if chain:
                self._current_model = chain[0]
                self._switch_count += 1
                return chain[0]
        return None

    def reset(self) -> None:
        self._current_model = self._config.default_model
