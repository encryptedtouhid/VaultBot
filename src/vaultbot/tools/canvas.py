"""Canvas/collaborative workspace for interactive editing.

Provides a shared document workspace between user and bot for
collaborative editing of text, code, and structured data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class CanvasType(str, Enum):
    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"
    TABLE = "table"


@dataclass
class CanvasRevision:
    content: str
    author: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    revision_id: int = 0


@dataclass
class Canvas:
    id: str
    title: str
    canvas_type: CanvasType = CanvasType.TEXT
    content: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    revisions: list[CanvasRevision] = field(default_factory=list)

    def update(self, content: str, author: str) -> CanvasRevision:
        rev = CanvasRevision(
            content=content,
            author=author,
            revision_id=len(self.revisions) + 1,
        )
        self.revisions.append(rev)
        self.content = content
        return rev

    def undo(self) -> str | None:
        if len(self.revisions) > 1:
            self.revisions.pop()
            self.content = self.revisions[-1].content
            return self.content
        return None


class CanvasManager:
    def __init__(self) -> None:
        self._canvases: dict[str, Canvas] = {}
        self._counter: int = 0

    def create(self, title: str, canvas_type: CanvasType = CanvasType.TEXT) -> Canvas:
        self._counter += 1
        canvas = Canvas(id=f"canvas_{self._counter}", title=title, canvas_type=canvas_type)
        self._canvases[canvas.id] = canvas
        return canvas

    def get(self, canvas_id: str) -> Canvas | None:
        return self._canvases.get(canvas_id)

    def delete(self, canvas_id: str) -> bool:
        if canvas_id in self._canvases:
            del self._canvases[canvas_id]
            return True
        return False

    def list_canvases(self) -> list[Canvas]:
        return list(self._canvases.values())

    @property
    def count(self) -> int:
        return len(self._canvases)
