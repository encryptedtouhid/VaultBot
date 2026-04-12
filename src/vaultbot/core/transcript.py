"""Transcript management with versioning and DAG preservation."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class TranscriptVersion:
    version_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    parent_id: str = ""
    messages_hash: str = ""
    created_at: float = field(default_factory=time.time)
    message_count: int = 0


class TranscriptManager:
    """Manages transcript versions as a DAG for safe rewriting."""

    def __init__(self) -> None:
        self._versions: dict[str, list[TranscriptVersion]] = {}

    def create_version(
        self, session_id: str, parent_id: str = "", message_count: int = 0
    ) -> TranscriptVersion:
        version = TranscriptVersion(parent_id=parent_id, message_count=message_count)
        self._versions.setdefault(session_id, []).append(version)
        return version

    def get_versions(self, session_id: str) -> list[TranscriptVersion]:
        return list(self._versions.get(session_id, []))

    def get_latest(self, session_id: str) -> TranscriptVersion | None:
        versions = self._versions.get(session_id, [])
        return versions[-1] if versions else None

    def branch(self, session_id: str) -> TranscriptVersion | None:
        """Create a new branch from the latest version."""
        latest = self.get_latest(session_id)
        if not latest:
            return None
        return self.create_version(
            session_id,
            parent_id=latest.version_id,
            message_count=latest.message_count,
        )

    def version_count(self, session_id: str) -> int:
        return len(self._versions.get(session_id, []))
