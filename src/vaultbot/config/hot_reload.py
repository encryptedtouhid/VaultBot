"""Hot-reload config with atomic writes and listeners."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

ConfigListener = Callable[[dict[str, object]], None]


@dataclass(slots=True)
class ConfigSnapshot:
    data: dict[str, object] = field(default_factory=dict)
    loaded_at: float = field(default_factory=time.time)
    version: int = 0


class HotReloadConfig:
    """Configuration with hot-reload support."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}
        self._listeners: list[ConfigListener] = []
        self._version = 0
        self._last_reload = 0.0

    @property
    def version(self) -> int:
        return self._version

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def set(self, key: str, value: object) -> None:
        self._data[key] = value
        self._version += 1
        self._notify()

    def patch(self, updates: dict[str, object]) -> None:
        self._data.update(updates)
        self._version += 1
        self._notify()

    def add_listener(self, listener: ConfigListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: ConfigListener) -> bool:
        if listener in self._listeners:
            self._listeners.remove(listener)
            return True
        return False

    def snapshot(self) -> ConfigSnapshot:
        return ConfigSnapshot(data=dict(self._data), version=self._version)

    def reload(self, data: dict[str, object]) -> None:
        self._data = dict(data)
        self._version += 1
        self._last_reload = time.time()
        self._notify()
        logger.info("config_reloaded", version=self._version)

    def _notify(self) -> None:
        for listener in self._listeners:
            try:
                listener(dict(self._data))
            except Exception as exc:
                logger.warning("config_listener_error", error=str(exc))


def validate_config(data: dict[str, object], schema: dict[str, type]) -> list[str]:
    """Validate config against a type schema. Returns list of errors."""
    errors: list[str] = []
    for key, expected_type in schema.items():
        if key not in data:
            errors.append(f"Missing required key: {key}")
        elif not isinstance(data[key], expected_type):
            errors.append(f"Invalid type for {key}: expected {expected_type.__name__}")
    return errors
