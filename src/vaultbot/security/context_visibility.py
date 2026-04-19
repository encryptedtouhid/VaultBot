"""Role-based context filtering with scope awareness.

Controls what information each role can see. Administrators see everything,
operators see operational data, and viewers see only public information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    GUEST = "guest"


class Scope(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    SECRET = "secret"


_ROLE_SCOPES: dict[Role, frozenset[Scope]] = {
    Role.ADMIN: frozenset(
        {Scope.PUBLIC, Scope.INTERNAL, Scope.SENSITIVE, Scope.SECRET}
    ),
    Role.OPERATOR: frozenset(
        {Scope.PUBLIC, Scope.INTERNAL, Scope.SENSITIVE}
    ),
    Role.VIEWER: frozenset({Scope.PUBLIC, Scope.INTERNAL}),
    Role.GUEST: frozenset({Scope.PUBLIC}),
}


@dataclass(frozen=True, slots=True)
class ContextItem:
    key: str
    value: Any
    scope: Scope = Scope.PUBLIC
    description: str = ""


@dataclass(slots=True)
class ContextVisibilityFilter:
    _items: list[ContextItem] = field(default_factory=list)

    def add_item(self, item: ContextItem) -> None:
        self._items.append(item)

    def add_items(self, items: list[ContextItem]) -> None:
        self._items.extend(items)

    def visible_items(self, role: Role) -> list[ContextItem]:
        granted = _ROLE_SCOPES.get(role, frozenset())
        result = [item for item in self._items if item.scope in granted]
        logger.debug(
            "context_filtered",
            role=role.value,
            total=len(self._items),
            visible=len(result),
        )
        return result

    def can_see(self, role: Role, scope: Scope) -> bool:
        granted = _ROLE_SCOPES.get(role, frozenset())
        return scope in granted

    def redact(self, role: Role) -> dict[str, Any]:
        granted = _ROLE_SCOPES.get(role, frozenset())
        result: dict[str, Any] = {}
        for item in self._items:
            if item.scope in granted:
                result[item.key] = item.value
            else:
                result[item.key] = "[REDACTED]"
        return result

    @property
    def item_count(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()
