"""Image analysis with multi-model fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class VisionRequest:
    image_data: bytes = b""
    image_url: str = ""
    question: str = "Describe this image"
    max_tokens: int = 1024


@dataclass(frozen=True, slots=True)
class VisionResult:
    description: str
    provider: str = ""
    model: str = ""
    confidence: float = 0.0


@runtime_checkable
class VisionProvider(Protocol):
    @property
    def provider_name(self) -> str: ...
    async def analyze(self, request: VisionRequest) -> VisionResult: ...


class VisionEngine:
    """Multi-model vision analysis with fallback."""

    def __init__(self) -> None:
        self._providers: dict[str, VisionProvider] = {}
        self._fallback_order: list[str] = []
        self._analysis_count = 0

    def register(self, provider: VisionProvider, priority: int = 0) -> None:
        self._providers[provider.provider_name] = provider
        self._fallback_order.append(provider.provider_name)
        self._fallback_order.sort()

    async def analyze(self, request: VisionRequest, provider: str = "") -> VisionResult:
        if provider and provider in self._providers:
            result = await self._providers[provider].analyze(request)
            self._analysis_count += 1
            return result

        for name in self._fallback_order:
            try:
                result = await self._providers[name].analyze(request)
                self._analysis_count += 1
                return result
            except Exception as exc:
                logger.warning("vision_fallback", provider=name, error=str(exc))
                continue

        raise RuntimeError("All vision providers failed")

    @property
    def analysis_count(self) -> int:
        return self._analysis_count

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())
