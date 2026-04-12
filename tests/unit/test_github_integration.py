"""Unit tests for GitHub integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.integrations.github_client import GitHubClient


def _mock_client(json_data: object) -> AsyncMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=json_data)
    client = AsyncMock()
    client.get = AsyncMock(return_value=mock_resp)
    client.post = AsyncMock(return_value=mock_resp)
    return client


class TestGitHubClient:
    def test_provider_name(self) -> None:
        c = GitHubClient(token="t", owner="o", repo="r")
        assert c.provider_name == "github"

    @pytest.mark.asyncio
    async def test_list_issues(self) -> None:
        c = GitHubClient(token="t", owner="o", repo="r")
        c._client = _mock_client([{"number": 1, "title": "Bug", "state": "open", "body": "desc"}])
        issues = await c.list_issues()
        assert len(issues) == 1
        assert issues[0].title == "Bug"

    @pytest.mark.asyncio
    async def test_create_issue(self) -> None:
        c = GitHubClient(token="t", owner="o", repo="r")
        c._client = _mock_client({"number": 42, "title": "New", "state": "open"})
        issue = await c.create_issue("New", "Body")
        assert issue.number == 42

    @pytest.mark.asyncio
    async def test_list_prs(self) -> None:
        c = GitHubClient(token="t", owner="o", repo="r")
        c._client = _mock_client(
            [
                {
                    "number": 10,
                    "title": "Feature",
                    "state": "open",
                    "base": {"ref": "main"},
                    "head": {"ref": "feat/x"},
                }
            ]
        )
        prs = await c.list_prs()
        assert len(prs) == 1
        assert prs[0].head == "feat/x"
