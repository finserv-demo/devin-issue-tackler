import logging

import httpx

from orchestrator.schemas.github import GitHubComment, GitHubIssue, PullRequest, TimelineEvent

logger = logging.getLogger(__name__)

_GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Async GitHub REST API client for issue and label operations."""

    def __init__(self, token: str, repo: str) -> None:
        """Initialize the client.

        Args:
            token: GitHub PAT or App token.
            repo: Repository in "owner/repo" format.
        """
        self._repo = repo
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _url(self, path: str) -> str:
        return f"{_GITHUB_API_BASE}/repos/{self._repo}{path}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | list | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method,
                self._url(path),
                headers=self._headers,
                json=json,
                params=params,
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp

    # ── Issue operations ──

    async def get_issue(self, number: int) -> GitHubIssue:
        """Fetch a single issue by number."""
        resp = await self._request("GET", f"/issues/{number}")
        data = resp.json()
        return GitHubIssue(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            labels=[label["name"] for label in data.get("labels", [])],
            state=data["state"],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            html_url=data.get("html_url", ""),
        )

    async def list_issues(
        self,
        state: str = "open",
        labels: list[str] | None = None,
    ) -> list[GitHubIssue]:
        """List issues, optionally filtered by labels. Paginates automatically."""
        all_issues: list[GitHubIssue] = []
        page = 1
        while True:
            params: dict[str, str | int] = {"state": state, "per_page": 100, "page": page}
            if labels:
                params["labels"] = ",".join(labels)
            resp = await self._request("GET", "/issues", params=params)
            items = resp.json()
            if not items:
                break
            for data in items:
                # Skip pull requests (GitHub returns them in /issues)
                if "pull_request" in data:
                    continue
                all_issues.append(
                    GitHubIssue(
                        number=data["number"],
                        title=data["title"],
                        body=data.get("body"),
                        labels=[label["name"] for label in data.get("labels", [])],
                        state=data["state"],
                        created_at=data.get("created_at", ""),
                        updated_at=data.get("updated_at", ""),
                        html_url=data.get("html_url", ""),
                    )
                )
            if len(items) < 100:
                break
            page += 1
        return all_issues

    async def get_issue_comments(self, number: int) -> list[GitHubComment]:
        """Fetch all comments on an issue. Paginates automatically."""
        all_comments: list[GitHubComment] = []
        page = 1
        while True:
            resp = await self._request(
                "GET",
                f"/issues/{number}/comments",
                params={"per_page": 100, "page": page},
            )
            items = resp.json()
            if not items:
                break
            for data in items:
                all_comments.append(
                    GitHubComment(
                        id=data["id"],
                        author=data.get("user", {}).get("login", ""),
                        body=data.get("body", ""),
                        created_at=data.get("created_at", ""),
                    )
                )
            if len(items) < 100:
                break
            page += 1
        return all_comments

    async def post_comment(self, number: int, body: str) -> GitHubComment:
        """Post a comment on an issue."""
        resp = await self._request("POST", f"/issues/{number}/comments", json={"body": body})
        data = resp.json()
        return GitHubComment(
            id=data["id"],
            author=data.get("user", {}).get("login", ""),
            body=data.get("body", ""),
            created_at=data.get("created_at", ""),
        )

    async def close_issue(self, number: int) -> None:
        """Close an issue."""
        await self._request("PATCH", f"/issues/{number}", json={"state": "closed"})

    # ── Label operations ──

    async def get_labels(self, number: int) -> list[str]:
        """Get all labels on an issue."""
        resp = await self._request("GET", f"/issues/{number}/labels")
        return [label["name"] for label in resp.json()]

    async def add_label(self, number: int, label: str) -> None:
        """Add a label to an issue."""
        await self._request("POST", f"/issues/{number}/labels", json={"labels": [label]})

    async def remove_label(self, number: int, label: str) -> None:
        """Remove a label from an issue. No-op if label doesn't exist."""
        try:
            await self._request("DELETE", f"/issues/{number}/labels/{label}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.debug("Label %r not found on issue #%d, skipping removal", label, number)
            else:
                raise

    async def swap_label(self, number: int, old_label: str, new_label: str) -> None:
        """Remove old label and add new label. Adds new even if remove fails."""
        await self.remove_label(number, old_label)
        await self.add_label(number, new_label)

    async def remove_all_devin_labels(self, number: int) -> None:
        """Remove devin status/control labels from an issue.

        Preserves sizing labels (devin:small, devin:medium, devin:large)
        so that dashboard metrics remain accurate after issue closure.
        """
        sizing_labels = {"devin:small", "devin:medium", "devin:large"}
        labels = await self.get_labels(number)
        for label in labels:
            if label.startswith("devin:") and label not in sizing_labels:
                await self.remove_label(number, label)

    async def ensure_labels_exist(self, labels: dict[str, str]) -> None:
        """Create labels on the repo if they don't already exist.

        Args:
            labels: Mapping of label name to hex color (without #).
        """
        existing: set[str] = set()
        page = 1
        while True:
            resp = await self._request("GET", "/labels", params={"per_page": 100, "page": page})
            items = resp.json()
            if not items:
                break
            existing.update(label["name"] for label in items)
            if len(items) < 100:
                break
            page += 1

        for name, color in labels.items():
            if name not in existing:
                try:
                    await self._request(
                        "POST",
                        "/labels",
                        json={"name": name, "color": color},
                    )
                    logger.info("Created label: %s", name)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 422:
                        logger.debug("Label %s already exists (race condition)", name)
                    else:
                        raise

    # ── Reaction operations ──

    async def add_reaction(self, number: int, reaction: str = "eyes") -> int:
        """Add a reaction to an issue. Returns the reaction ID."""
        resp = await self._request(
            "POST",
            f"/issues/{number}/reactions",
            json={"content": reaction},
        )
        return resp.json()["id"]

    async def remove_reaction(self, number: int, reaction_id: int) -> None:
        """Remove a reaction from an issue."""
        try:
            await self._request("DELETE", f"/issues/{number}/reactions/{reaction_id}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.debug("Reaction %d not found on issue #%d", reaction_id, number)
            else:
                raise

    # ── Timeline / history ──

    async def get_timeline_events(self, number: int) -> list[TimelineEvent]:
        """Fetch timeline events for an issue (label changes, etc.)."""
        all_events: list[TimelineEvent] = []
        page = 1
        while True:
            resp = await self._request(
                "GET",
                f"/issues/{number}/timeline",
                params={"per_page": 100, "page": page},
            )
            items = resp.json()
            if not items:
                break
            for data in items:
                event_type = data.get("event", "")
                label_name = None
                if event_type in ("labeled", "unlabeled"):
                    label_name = data.get("label", {}).get("name")
                all_events.append(
                    TimelineEvent(
                        event=event_type,
                        label=label_name,
                        created_at=data.get("created_at", ""),
                        actor=data.get("actor", {}).get("login", ""),
                    )
                )
            if len(items) < 100:
                break
            page += 1
        return all_events

    async def get_linked_pull_requests(self, number: int) -> list[PullRequest]:
        """Get pull requests linked to an issue via timeline events."""
        events = await self.get_timeline_events(number)
        pr_numbers: set[int] = set()
        prs: list[PullRequest] = []

        for event in events:
            if event.event in ("cross-referenced", "connected"):
                # These events may reference PRs — would need additional parsing
                pass

        # Fallback: search for PRs that mention the issue
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_GITHUB_API_BASE}/search/issues",
                    headers=self._headers,
                    params={"q": f"repo:{self._repo} is:pr {number}"},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    for item in resp.json().get("items", []):
                        pr_num = item["number"]
                        if pr_num not in pr_numbers:
                            pr_numbers.add(pr_num)
                            prs.append(
                                PullRequest(
                                    number=pr_num,
                                    title=item.get("title", ""),
                                    state=item.get("state", "open"),
                                    html_url=item.get("html_url", ""),
                                    merged_at=item.get("pull_request", {}).get("merged_at"),
                                )
                            )
        except (httpx.HTTPStatusError, httpx.TransportError):
            logger.warning("Failed to search for linked PRs for issue #%d", number)

        return prs
