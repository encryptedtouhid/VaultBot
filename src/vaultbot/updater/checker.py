"""Version checker for PyPI and GitHub releases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class UpdateChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"
    NIGHTLY = "nightly"


@dataclass(frozen=True, slots=True)
class VersionInfo:
    current: str
    latest: str
    channel: UpdateChannel
    update_available: bool
    release_url: str = ""


class VersionChecker:
    """Check for available updates from PyPI or GitHub."""

    def __init__(
        self,
        current_version: str = "0.1.0",
        package_name: str = "vaultbot",
        github_repo: str = "encryptedtouhid/VaultBot",
    ) -> None:
        self._current = current_version
        self._package = package_name
        self._repo = github_repo
        self._client = httpx.AsyncClient(timeout=15.0)

    @property
    def current_version(self) -> str:
        return self._current

    async def check_pypi(self) -> VersionInfo:
        """Check PyPI for the latest version."""
        try:
            resp = await self._client.get(f"https://pypi.org/pypi/{self._package}/json")
            resp.raise_for_status()
            latest = resp.json().get("info", {}).get("version", self._current)
            return VersionInfo(
                current=self._current,
                latest=latest,
                channel=UpdateChannel.STABLE,
                update_available=latest != self._current,
                release_url=f"https://pypi.org/project/{self._package}/{latest}/",
            )
        except Exception as exc:
            logger.warning("pypi_check_failed", error=str(exc))
            return VersionInfo(
                current=self._current,
                latest=self._current,
                channel=UpdateChannel.STABLE,
                update_available=False,
            )

    async def check_github(self) -> VersionInfo:
        """Check GitHub releases for the latest version."""
        try:
            resp = await self._client.get(
                f"https://api.github.com/repos/{self._repo}/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            data = resp.json()
            latest = data.get("tag_name", self._current).lstrip("v")
            is_pre = data.get("prerelease", False)
            channel = UpdateChannel.BETA if is_pre else UpdateChannel.STABLE
            return VersionInfo(
                current=self._current,
                latest=latest,
                channel=channel,
                update_available=latest != self._current,
                release_url=data.get("html_url", ""),
            )
        except Exception as exc:
            logger.warning("github_check_failed", error=str(exc))
            return VersionInfo(
                current=self._current,
                latest=self._current,
                channel=UpdateChannel.STABLE,
                update_available=False,
            )

    async def close(self) -> None:
        await self._client.aclose()
