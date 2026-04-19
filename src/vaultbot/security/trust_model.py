"""Trust chain verification for entities in the system.

Entities (plugins, users, channels) are assigned trust levels. A trust
chain links an entity back to a root of trust. Verification walks the
chain and ensures every link is valid and not expired.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class TrustEntity:
    entity_id: str
    entity_type: str
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    granted_by: str = ""
    granted_at: float = field(default_factory=time.time)
    expires_at: float = 0.0


@dataclass(frozen=True, slots=True)
class TrustVerification:
    valid: bool
    entity_id: str
    chain_length: int = 0
    effective_level: TrustLevel = TrustLevel.UNTRUSTED
    reason: str = ""


@dataclass(slots=True)
class TrustStore:
    """Manages a trust chain of entities."""

    _entities: dict[str, TrustEntity] = field(default_factory=dict)
    _root_id: str = "system"

    def __post_init__(self) -> None:
        if self._root_id not in self._entities:
            self._entities[self._root_id] = TrustEntity(
                entity_id=self._root_id,
                entity_type="system",
                trust_level=TrustLevel.FULL,
                granted_by="",
            )

    def register(self, entity: TrustEntity) -> bool:
        """Register an entity. Returns False if grantor is unknown."""
        if entity.granted_by and entity.granted_by not in self._entities:
            logger.warning(
                "trust_grantor_unknown",
                entity=entity.entity_id,
                grantor=entity.granted_by,
            )
            return False
        self._entities[entity.entity_id] = entity
        logger.info(
            "trust_entity_registered",
            entity=entity.entity_id,
            level=entity.trust_level.value,
        )
        return True

    def revoke(self, entity_id: str) -> bool:
        """Remove an entity from the store."""
        if entity_id == self._root_id:
            return False
        if entity_id in self._entities:
            del self._entities[entity_id]
            logger.info("trust_entity_revoked", entity=entity_id)
            return True
        return False

    def verify(self, entity_id: str) -> TrustVerification:
        """Verify the trust chain for an entity."""
        if entity_id not in self._entities:
            return TrustVerification(
                valid=False,
                entity_id=entity_id,
                reason="Entity not found in trust store",
            )
        chain: list[str] = []
        current_id = entity_id
        now = time.time()
        while current_id:
            if current_id in chain:
                return TrustVerification(
                    valid=False,
                    entity_id=entity_id,
                    chain_length=len(chain),
                    reason="Circular trust chain detected",
                )
            entity = self._entities.get(current_id)
            if entity is None:
                return TrustVerification(
                    valid=False,
                    entity_id=entity_id,
                    chain_length=len(chain),
                    reason=f"Broken chain at {current_id}",
                )
            if entity.expires_at > 0 and entity.expires_at < now:
                return TrustVerification(
                    valid=False,
                    entity_id=entity_id,
                    chain_length=len(chain),
                    reason=f"Entity {current_id} has expired",
                )
            chain.append(current_id)
            current_id = entity.granted_by
        root_entity = self._entities.get(chain[-1])
        if root_entity is None or root_entity.entity_id != self._root_id:
            return TrustVerification(
                valid=False,
                entity_id=entity_id,
                chain_length=len(chain),
                reason="Chain does not reach root of trust",
            )
        target = self._entities[entity_id]
        return TrustVerification(
            valid=True,
            entity_id=entity_id,
            chain_length=len(chain),
            effective_level=target.trust_level,
        )

    def get_entity(self, entity_id: str) -> TrustEntity | None:
        """Retrieve an entity by ID."""
        return self._entities.get(entity_id)

    def is_trusted(
        self,
        entity_id: str,
        minimum: TrustLevel = TrustLevel.LOW,
    ) -> bool:
        """Check if entity is trusted at or above minimum level."""
        result = self.verify(entity_id)
        if not result.valid:
            return False
        return _LEVEL_ORDER.get(
            result.effective_level, 0
        ) >= _LEVEL_ORDER.get(minimum, 0)

    @property
    def entity_count(self) -> int:
        return len(self._entities)


_LEVEL_ORDER: dict[TrustLevel, int] = {
    TrustLevel.UNTRUSTED: 0,
    TrustLevel.LOW: 1,
    TrustLevel.MEDIUM: 2,
    TrustLevel.HIGH: 3,
    TrustLevel.FULL: 4,
}
