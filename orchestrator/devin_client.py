import asyncio
import logging

import httpx

from orchestrator.schemas.devin import DevinSession, Message, MessagePage, Playbook, SessionPullRequest

logger = logging.getLogger(__name__)

_DEVIN_API_V3_BASE = "https://api.devin.ai/v3"
_DEVIN_API_V1_BASE = "https://api.devin.ai/v1"

_ACTIVE_STATUSES = {"new", "claimed", "running", "resuming"}
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 5


class DevinClient:
    """Async Devin API v3 client for session lifecycle and message operations."""

    def __init__(self, api_key: str, org_id: str) -> None:
        """Initialize the client.

        Args:
            api_key: Devin API key (cog_* service user credential or apk_*).
            org_id: Devin organization ID.
        """
        self._api_key = api_key
        self._org_id = org_id
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _v3_url(self, path: str) -> str:
        return f"{_DEVIN_API_V3_BASE}/organizations/{self._org_id}{path}"

    def _v1_url(self, path: str) -> str:
        return f"{_DEVIN_API_V1_BASE}{path}"

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict | list | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with retry on 429 (rate limit)."""
        for attempt in range(_MAX_RETRIES):
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method,
                    url,
                    headers=self._headers,
                    json=json,
                    params=params,
                    timeout=60.0,
                )
                if resp.status_code == 429:
                    wait = _INITIAL_BACKOFF_SECONDS * (2**attempt)
                    logger.warning("Rate limited by Devin API, retrying in %ds (attempt %d/%d)", wait, attempt + 1, _MAX_RETRIES)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
        raise httpx.HTTPStatusError(
            "Max retries exceeded (429 rate limit)",
            request=httpx.Request(method, url),
            response=resp,
        )

    # ── Session lifecycle ──

    async def create_session(
        self,
        prompt: str,
        playbook_id: str | None = None,
        tags: list[str] | None = None,
        max_acu_limit: int | None = None,
    ) -> DevinSession:
        """Create a new Devin session.

        Args:
            prompt: Task description for Devin.
            playbook_id: Optional playbook to attach.
            tags: Optional tags for filtering/organizing.
            max_acu_limit: Optional ACU consumption cap.

        Returns:
            The created DevinSession.
        """
        body: dict = {"prompt": prompt}
        if playbook_id:
            body["playbook_id"] = playbook_id
        if tags:
            body["tags"] = tags
        if max_acu_limit is not None:
            body["max_acu_limit"] = max_acu_limit

        resp = await self._request("POST", self._v3_url("/sessions"), json=body)
        data = resp.json()
        return self._parse_session(data)

    async def get_session(self, session_id: str) -> DevinSession:
        """Get session details by ID."""
        resp = await self._request("GET", self._v3_url(f"/sessions/{session_id}"))
        return self._parse_session(resp.json())

    async def send_message(self, session_id: str, message: str) -> None:
        """Send a message to an active session. Auto-resumes suspended sessions."""
        await self._request(
            "POST",
            self._v3_url(f"/sessions/{session_id}/messages"),
            json={"message": message},
        )

    async def terminate_session(self, session_id: str) -> None:
        """Terminate a session. Cannot be resumed after termination."""
        await self._request("DELETE", self._v3_url(f"/sessions/{session_id}"))

    # ── Query helpers ──

    async def list_sessions_by_tags(self, tags: list[str]) -> list[DevinSession]:
        """List sessions filtered by tags using the v1 API.

        Args:
            tags: List of tags to filter by (all must match).

        Returns:
            List of matching sessions.
        """
        params: dict[str, str | int] = {"limit": 100}
        # v1 API supports tag filtering via repeated query params (?tags=a&tags=b)
        resp = await self._request(
            "GET",
            self._v1_url("/sessions"),
            params={**params, "tags": tags},
        )
        data = resp.json()
        sessions_data = data.get("sessions", data) if isinstance(data, dict) else data
        return [self._parse_session_v1(s) for s in sessions_data]

    async def get_sessions_for_issue(self, issue_number: int) -> list[DevinSession]:
        """Get all sessions associated with a GitHub issue.

        Uses tag convention: backlog-auto + issue:{number}
        """
        return await self.list_sessions_by_tags(["backlog-auto", f"issue:{issue_number}"])

    async def get_active_session_for_issue(self, issue_number: int) -> DevinSession | None:
        """Get the currently active session for an issue, or None.

        A session is "active" if its status is in (new, claimed, running, resuming).
        """
        sessions = await self.get_sessions_for_issue(issue_number)
        for session in sessions:
            if session.status in _ACTIVE_STATUSES:
                return session
        return None

    # ── Message polling ──

    async def list_messages(
        self,
        session_id: str,
        after: str | None = None,
        first: int = 100,
    ) -> MessagePage:
        """List messages from a session with cursor-based pagination.

        Args:
            session_id: The Devin session ID.
            after: Cursor for pagination (from previous response's end_cursor).
            first: Number of messages to fetch (max 100).

        Returns:
            MessagePage with items, has_next_page, and end_cursor.
        """
        params: dict[str, str | int] = {"first": first}
        if after:
            params["after"] = after

        resp = await self._request(
            "GET",
            self._v3_url(f"/sessions/{session_id}/messages"),
            params=params,
        )
        data = resp.json()
        items = [
            Message(
                event_id=msg.get("event_id", ""),
                source=msg.get("source", ""),
                message=msg.get("message", ""),
                created_at=msg.get("created_at", 0),
            )
            for msg in data.get("items", [])
        ]
        return MessagePage(
            items=items,
            has_next_page=data.get("has_next_page", False),
            end_cursor=data.get("end_cursor"),
        )

    # ── Playbook management (v1 API) ──

    async def create_playbook(self, title: str, body: str) -> str:
        """Create a new playbook. Returns the playbook_id."""
        resp = await self._request(
            "POST",
            self._v1_url("/playbooks"),
            json={"title": title, "body": body},
        )
        return resp.json()["playbook_id"]

    async def list_playbooks(self) -> list[Playbook]:
        """List all playbooks in the organization."""
        resp = await self._request("GET", self._v1_url("/playbooks"))
        data = resp.json()
        playbooks_list = data if isinstance(data, list) else data.get("playbooks", [])
        return [
            Playbook(
                playbook_id=p["playbook_id"],
                title=p.get("title", ""),
                body=p.get("body", ""),
                status=p.get("status", ""),
            )
            for p in playbooks_list
        ]

    async def update_playbook(self, playbook_id: str, title: str, body: str) -> None:
        """Update an existing playbook."""
        await self._request(
            "PUT",
            self._v1_url(f"/playbooks/{playbook_id}"),
            json={"title": title, "body": body},
        )

    # ── Internal helpers ──

    @staticmethod
    def _parse_session(data: dict) -> DevinSession:
        """Parse a v3 session response into a DevinSession."""
        return DevinSession(
            session_id=data.get("session_id", ""),
            url=data.get("url", ""),
            status=data.get("status", "new"),
            acus_consumed=data.get("acus_consumed", 0.0),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            tags=data.get("tags", []),
            pull_requests=[
                SessionPullRequest(pr_url=pr.get("pr_url", ""), pr_state=pr.get("pr_state", ""))
                for pr in data.get("pull_requests", [])
            ],
        )

    @staticmethod
    def _parse_session_v1(data: dict) -> DevinSession:
        """Parse a v1 session response into a DevinSession."""
        # v1 uses status_enum instead of status
        status = data.get("status_enum", data.get("status", ""))
        # Map v1 statuses to v3-style
        v1_to_v3_status = {
            "working": "running",
            "blocked": "suspended",
            "finished": "exit",
            "expired": "exit",
        }
        mapped_status = v1_to_v3_status.get(status, status)

        return DevinSession(
            session_id=data.get("session_id", ""),
            url=data.get("url", ""),
            status=mapped_status,
            acus_consumed=data.get("acus_consumed", 0.0),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            tags=data.get("tags", []),
            pull_requests=[
                SessionPullRequest(pr_url=pr.get("pr_url", ""), pr_state=pr.get("pr_state", ""))
                for pr in data.get("pull_requests", [])
            ],
        )
