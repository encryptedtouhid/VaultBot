"""Unit tests for update checker."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.updater.checker import UpdateChannel, VersionChecker, VersionInfo


class TestVersionInfo:
    def test_no_update(self) -> None:
        info = VersionInfo(
            current="1.0.0", latest="1.0.0", channel=UpdateChannel.STABLE, update_available=False
        )
        assert not info.update_available

    def test_update_available(self) -> None:
        info = VersionInfo(
            current="1.0.0", latest="1.1.0", channel=UpdateChannel.STABLE, update_available=True
        )
        assert info.update_available


class TestVersionChecker:
    def test_current_version(self) -> None:
        checker = VersionChecker(current_version="0.2.0")
        assert checker.current_version == "0.2.0"

    @pytest.mark.asyncio
    async def test_check_pypi_success(self) -> None:
        checker = VersionChecker(current_version="0.1.0")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"info": {"version": "0.2.0"}})
        checker._client = AsyncMock()
        checker._client.get = AsyncMock(return_value=mock_resp)

        info = await checker.check_pypi()
        assert info.latest == "0.2.0"
        assert info.update_available is True

    @pytest.mark.asyncio
    async def test_check_pypi_failure(self) -> None:
        checker = VersionChecker(current_version="0.1.0")
        checker._client = AsyncMock()
        checker._client.get = AsyncMock(side_effect=Exception("network error"))

        info = await checker.check_pypi()
        assert info.update_available is False

    @pytest.mark.asyncio
    async def test_check_github_success(self) -> None:
        checker = VersionChecker(current_version="0.1.0")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(
            return_value={
                "tag_name": "v0.3.0",
                "prerelease": False,
                "html_url": "https://github.com/test/releases/v0.3.0",
            }
        )
        checker._client = AsyncMock()
        checker._client.get = AsyncMock(return_value=mock_resp)

        info = await checker.check_github()
        assert info.latest == "0.3.0"
        assert info.channel == UpdateChannel.STABLE
        assert info.update_available is True

    @pytest.mark.asyncio
    async def test_check_github_prerelease(self) -> None:
        checker = VersionChecker(current_version="0.1.0")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(
            return_value={"tag_name": "v0.2.0-beta.1", "prerelease": True, "html_url": ""}
        )
        checker._client = AsyncMock()
        checker._client.get = AsyncMock(return_value=mock_resp)

        info = await checker.check_github()
        assert info.channel == UpdateChannel.BETA
