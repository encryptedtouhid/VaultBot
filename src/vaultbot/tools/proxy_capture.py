"""HTTP proxy capture for debugging and request logging."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CapturedRequest:
    method: str
    url: str
    status_code: int = 0
    request_headers: dict[str, str] = field(default_factory=dict)
    response_size: int = 0
    duration_ms: int = 0
    timestamp: float = field(default_factory=time.time)


class ProxyCaptureStore:
    """Stores captured HTTP requests for debugging."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._entries: list[CapturedRequest] = []
        self._max_entries = max_entries

    @property
    def count(self) -> int:
        return len(self._entries)

    def record(self, request: CapturedRequest) -> None:
        self._entries.append(request)
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)

    def search(self, url_pattern: str = "", method: str = "") -> list[CapturedRequest]:
        results = self._entries
        if url_pattern:
            results = [r for r in results if url_pattern in r.url]
        if method:
            results = [r for r in results if r.method == method.upper()]
        return results

    def get_recent(self, limit: int = 50) -> list[CapturedRequest]:
        return self._entries[-limit:]

    def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        return count

    def stats(self) -> dict[str, int]:
        methods: dict[str, int] = {}
        for r in self._entries:
            methods[r.method] = methods.get(r.method, 0) + 1
        return methods
