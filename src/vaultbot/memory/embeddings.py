"""Multi-backend embedding engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vector: list[float]
    model: str = ""
    dimensions: int = 0
    token_count: int = 0


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def provider_name(self) -> str: ...
    async def embed(self, text: str) -> EmbeddingResult: ...
    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]: ...


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._model = model
        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            timeout=30.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    async def embed(self, text: str) -> EmbeddingResult:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        resp = await self._client.post(
            "/embeddings",
            json={"input": texts, "model": self._model},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            EmbeddingResult(
                vector=item["embedding"],
                model=self._model,
                dimensions=len(item["embedding"]),
                token_count=data.get("usage", {}).get("total_tokens", 0),
            )
            for item in data.get("data", [])
        ]

    async def close(self) -> None:
        await self._client.aclose()


class EmbeddingEngine:
    """Multi-provider embedding engine."""

    def __init__(self) -> None:
        self._providers: dict[str, EmbeddingProvider] = {}
        self._default: str = ""
        self._embed_count = 0

    def register(self, provider: EmbeddingProvider) -> None:
        self._providers[provider.provider_name] = provider
        if not self._default:
            self._default = provider.provider_name

    async def embed(self, text: str, provider: str = "") -> EmbeddingResult:
        name = provider or self._default
        if not name or name not in self._providers:
            raise ValueError(f"Unknown embedding provider: {name}")
        result = await self._providers[name].embed(text)
        self._embed_count += 1
        return result

    async def embed_batch(self, texts: list[str], provider: str = "") -> list[EmbeddingResult]:
        name = provider or self._default
        if not name or name not in self._providers:
            raise ValueError(f"Unknown embedding provider: {name}")
        results = await self._providers[name].embed_batch(texts)
        self._embed_count += len(texts)
        return results

    @property
    def embed_count(self) -> int:
        return self._embed_count
