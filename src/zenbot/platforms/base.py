"""Abstract platform adapter protocol.

Any class that implements these methods can serve as a messaging platform
adapter — no inheritance required (structural subtyping via Protocol).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from zenbot.core.message import InboundMessage, OutboundMessage


@runtime_checkable
class PlatformAdapter(Protocol):
    """Protocol that all messaging platform adapters must satisfy."""

    @property
    def platform_name(self) -> str:
        """Unique name identifying this platform (e.g., 'telegram', 'discord')."""
        ...

    async def connect(self) -> None:
        """Establish connection to the messaging platform."""
        ...

    async def disconnect(self) -> None:
        """Gracefully disconnect from the platform."""
        ...

    async def listen(self) -> AsyncIterator[InboundMessage]:
        """Yield incoming messages as they arrive."""
        ...

    async def send(self, message: OutboundMessage) -> None:
        """Send a message to the platform."""
        ...

    async def healthcheck(self) -> bool:
        """Check if the platform connection is healthy."""
        ...
