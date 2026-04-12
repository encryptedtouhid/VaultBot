"""GitHub API client for issues, PRs, and repos."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_API_URL = "https://api.github.com"


@dataclass(frozen=True, slots=True)
class GitHubIssue:
    number: int
    title: str
    state: str = "open"
    body: str = ""
    labels: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GitHubPR:
    number: int
    title: str
    state: str = "open"
    base: str = "main"
    head: str = ""


class GitHubClient:
    """GitHub API client."""

    def __init__(self, token: str, owner: str = "", repo: str = "") -> None:
        self._owner = owner
        self._repo = repo
        self._client = httpx.AsyncClient(
            base_url=_API_URL,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

    @property
    def provider_name(self) -> str:
        return "github"

    async def list_issues(self, state: str = "open") -> list[GitHubIssue]:
        resp = await self._client.get(
            f"/repos/{self._owner}/{self._repo}/issues",
            params={"state": state},
        )
        resp.raise_for_status()
        return [
            GitHubIssue(
                number=i["number"],
                title=i["title"],
                state=i["state"],
                body=i.get("body", ""),
            )
            for i in resp.json()
        ]

    async def create_issue(self, title: str, body: str = "") -> GitHubIssue:
        resp = await self._client.post(
            f"/repos/{self._owner}/{self._repo}/issues",
            json={"title": title, "body": body},
        )
        resp.raise_for_status()
        data = resp.json()
        return GitHubIssue(number=data["number"], title=data["title"], state=data["state"])

    async def list_prs(self, state: str = "open") -> list[GitHubPR]:
        resp = await self._client.get(
            f"/repos/{self._owner}/{self._repo}/pulls",
            params={"state": state},
        )
        resp.raise_for_status()
        return [
            GitHubPR(
                number=p["number"],
                title=p["title"],
                state=p["state"],
                base=p.get("base", {}).get("ref", "main"),
                head=p.get("head", {}).get("ref", ""),
            )
            for p in resp.json()
        ]

    async def close(self) -> None:
        await self._client.aclose()
