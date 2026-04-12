"""Model selection and switching CLI commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelInfo:
    model_id: str
    provider: str = ""
    context_window: int = 0
    is_default: bool = False


class ModelCommands:
    """CLI commands for model management."""

    def __init__(self) -> None:
        self._models: dict[str, ModelInfo] = {}
        self._current: str = ""

    def list_models(self) -> list[ModelInfo]:
        return list(self._models.values())

    def add_model(self, model_id: str, provider: str = "", context_window: int = 0) -> ModelInfo:
        info = ModelInfo(
            model_id=model_id,
            provider=provider,
            context_window=context_window,
            is_default=not self._current,
        )
        self._models[model_id] = info
        if not self._current:
            self._current = model_id
        return info

    def set_default(self, model_id: str) -> bool:
        if model_id in self._models:
            self._current = model_id
            return True
        return False

    def get_default(self) -> str:
        return self._current
