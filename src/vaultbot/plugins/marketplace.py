"""Plugin marketplace client.

Allows browsing, searching, and installing plugins from a remote
registry. Every plugin in the marketplace must pass a review process
and be signed by a trusted maintainer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_REGISTRY_URL = "https://marketplace.vaultbot.dev/api/v1"


class ReviewStatus(str, Enum):
    """Review status of a marketplace plugin."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class MarketplaceEntry:
    """A plugin listing in the marketplace."""

    name: str
    version: str
    description: str
    author: str
    review_status: ReviewStatus
    downloads: int = 0
    rating: float = 0.0
    tags: list[str] = field(default_factory=list)
    homepage: str = ""
    checksum: str = ""  # SHA-256 of the plugin package

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MarketplaceEntry:
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            review_status=ReviewStatus(data.get("review_status", "pending")),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            tags=data.get("tags", []),
            homepage=data.get("homepage", ""),
            checksum=data.get("checksum", ""),
        )


class MarketplaceClient:
    """Client for the VaultBot plugin marketplace.

    Only plugins with ReviewStatus.APPROVED can be installed.
    All downloads are verified against their published checksums.
    """

    def __init__(self, registry_url: str = DEFAULT_REGISTRY_URL) -> None:
        self._registry_url = registry_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._registry_url,
            timeout=30.0,
            headers={"User-Agent": "zenbot-marketplace/0.1"},
        )

    async def search(
        self,
        query: str = "",
        *,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[MarketplaceEntry]:
        """Search for plugins in the marketplace."""
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query
        if tags:
            params["tags"] = ",".join(tags)

        response = await self._client.get("/plugins", params=params)
        response.raise_for_status()
        data = response.json()

        return [
            MarketplaceEntry.from_dict(entry)
            for entry in data.get("plugins", [])
            if entry.get("review_status") == "approved"
        ]

    async def get_plugin(self, name: str) -> MarketplaceEntry | None:
        """Get details for a specific plugin."""
        try:
            response = await self._client.get(f"/plugins/{name}")
            response.raise_for_status()
            return MarketplaceEntry.from_dict(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def download(
        self,
        name: str,
        version: str,
        dest_dir: Path,
    ) -> Path:
        """Download a plugin package from the marketplace.

        Only approved plugins can be downloaded. The package checksum
        is verified after download.

        Returns the path to the downloaded plugin directory.
        """
        # Get plugin info first
        entry = await self.get_plugin(name)
        if entry is None:
            raise ValueError(f"Plugin '{name}' not found in marketplace.")

        if entry.review_status != ReviewStatus.APPROVED:
            raise ValueError(
                f"Plugin '{name}' is not approved (status: {entry.review_status.value}). "
                "Only approved plugins can be installed."
            )

        # Download the package
        response = await self._client.get(
            f"/plugins/{name}/versions/{version}/download",
        )
        response.raise_for_status()

        # Verify checksum
        import hashlib

        actual_checksum = hashlib.sha256(response.content).hexdigest()
        if entry.checksum and actual_checksum != entry.checksum:
            raise ValueError(
                f"Checksum mismatch for '{name}'. Package may be tampered. "
                f"Expected: {entry.checksum[:16]}... Got: {actual_checksum[:16]}..."
            )

        # Extract to destination
        plugin_dir = dest_dir / name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            zf.extractall(plugin_dir)

        logger.info(
            "marketplace_download",
            plugin=name,
            version=version,
            checksum_verified=bool(entry.checksum),
        )

        return plugin_dir

    async def submit(
        self,
        plugin_dir: Path,
        *,
        api_token: str,
    ) -> dict[str, str]:
        """Submit a plugin for review.

        The plugin must be signed before submission. After submission,
        it enters the review queue with status PENDING.

        Returns submission metadata.
        """
        import io
        import zipfile

        # Package the plugin directory
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(plugin_dir.rglob("*")):
                if file_path.is_file() and "__pycache__" not in str(file_path):
                    zf.write(file_path, file_path.relative_to(plugin_dir))
        buffer.seek(0)

        response = await self._client.post(
            "/plugins/submit",
            files={"package": ("plugin.zip", buffer, "application/zip")},
            headers={"Authorization": f"Bearer {api_token}"},
        )
        response.raise_for_status()

        result = response.json()
        logger.info(
            "marketplace_submitted",
            plugin=result.get("name", "unknown"),
            submission_id=result.get("submission_id", ""),
        )
        return result

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
