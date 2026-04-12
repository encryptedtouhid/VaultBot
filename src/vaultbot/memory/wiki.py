"""Wiki-style knowledge base for persistent information."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class WikiPage:
    """A wiki knowledge page."""

    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1


class WikiKnowledgeBase:
    """Wiki-style knowledge base with pages, links, and search."""

    def __init__(self) -> None:
        self._pages: dict[str, WikiPage] = {}

    @property
    def page_count(self) -> int:
        return len(self._pages)

    def create_page(self, title: str, content: str, tags: list[str] | None = None) -> WikiPage:
        """Create a new wiki page."""
        if title in self._pages:
            raise ValueError(f"Page '{title}' already exists")
        page = WikiPage(title=title, content=content, tags=tags or [])
        self._pages[title] = page
        logger.info("wiki_page_created", title=title)
        return page

    def get_page(self, title: str) -> WikiPage | None:
        return self._pages.get(title)

    def update_page(self, title: str, content: str) -> WikiPage:
        page = self._pages.get(title)
        if not page:
            raise KeyError(f"Page '{title}' not found")
        page.content = content
        page.updated_at = time.time()
        page.version += 1
        return page

    def delete_page(self, title: str) -> bool:
        if title in self._pages:
            del self._pages[title]
            return True
        return False

    def search(self, query: str) -> list[WikiPage]:
        """Search pages by title and content."""
        query_lower = query.lower()
        return [
            p
            for p in self._pages.values()
            if query_lower in p.title.lower() or query_lower in p.content.lower()
        ]

    def list_pages(self) -> list[str]:
        return list(self._pages.keys())

    def get_linked_pages(self, title: str) -> list[WikiPage]:
        """Get pages linked from a given page."""
        page = self._pages.get(title)
        if not page:
            return []
        return [self._pages[link] for link in page.links if link in self._pages]
