import asyncio
import logging

import httpx

from orchestrator.schemas.devin import DevinSession, Message, MessagePage, Playbook, SessionPullRequest

logger = logging.getLogger(__name__)

# Using the v1 API with apk_* service API keys. The v3 API with cog_* keys
# returns 403 on individual session endpoints (GET/POST/DELETE /sessions/{id}).
# v1 with apk_* keys supports all operations. Note that apk_* keys are marked
# as deprecated in the docs — if Devin fixes v3 permissions for cog_* keys,
# this client should be migrated back to v3.
_DEVIN_API_BASE = "https://api.devin.ai/v1"

_ACTIVE_STATUSES = {"new", "claimed", "running", "resuming"}
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 5


def _strip_devin_prefix(session_id: str) -> str:
    """Strip the 'devin-' prefix that the v1 API adds to session IDs."""
    return session_id.removeprefix("devin-")


def _add_devin_prefix(session_id: str) -> str:
    """Add the 'devin-' prefix that the v1 API expects on session IDs."""
    if session_id.startswith("devin-"):
        return session_id
    return f"devin-{session_id}"


class DevinClient:
    """Async Devin API v1 client for session lifecycle and message operations.

    Uses the v1 API with apk_* service API keys. The v3 API with cog_*
    service user keys does not support individual session operations (returns
    403). See PR #25 for details on this limitation.
    """

    def __init__(self, api_key: str, org_id: str) -> None:
        """Initialize the client.

        Args:
            api_key: Devin API key (apk_* service API key).
            org_id: Devin organization ID (retained for compatibility but
                not used in v1 URLs — v1 resolves org from the key).
        """
        self._api_key = api_key
        self._org_id = org_id
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{_DEVIN_API_BASE}{path}"

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
                    if attempt < _MAX_RETRIES - 1:
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

        resp = await self._request("POST", self._url("/sessions"), json=body)
        data = resp.json()
        return self._parse_session(data)

    async def get_session(self, session_id: str) -> DevinSession:
        """Get session details by ID."""
        v1_id = _add_devin_prefix(session_id)
        resp = await self._request("GET", self._url(f"/sessions/{v1_id}"))
        return self._parse_session(resp.json())

    async def send_message(self, session_id: str, message: str) -> None:
        """Send a message to an active session. Auto-resumes suspended sessions.

        Note: v1 uses /sessions/{id}/message (singular), not /messages.
        """
        v1_id = _add_devin_prefix(session_id)
        await self._request(
            "POST",
            self._url(f"/sessions/{v1_id}/message"),
            json={"message": message},
        )

    async def terminate_session(self, session_id: str) -> None:
        """Terminate a session. Cannot be resumed after termination."""
        v1_id = _add_devin_prefix(session_id)
        await self._request("DELETE", self._url(f"/sessions/{v1_id}"))

    # ── Query helpers ──

    async def list_sessions_by_tags(self, tags: list[str]) -> list[DevinSession]:
        """List sessions filtered by tags.

        Uses the v1 API's server-side tag filtering via the ?tags= parameter.
        Multiple tags are comma-separated and all must match (AND logic).

        Args:
            tags: List of tags to filter by (all must match).

        Returns:
            List of matching sessions.
        """
        params: dict[str, str | int] = {
            "tags": ",".join(tags),
            "limit": 100,
        }

        resp = await self._request(
            "GET",
            self._url("/sessions"),
            params=params,
        )
        data = resp.json()
        sessions_list = data.get("sessions", [])

        return [self._parse_session(item) for item in sessions_list]

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
        """List messages from a session.

        Note: v1 GET /sessions/{id} includes messages in the response.
        This method fetches the full session and extracts messages.

        Args:
            session_id: The Devin session ID.
            after: Not used in v1 (no cursor-based message pagination).
            first: Not used in v1 (all messages returned with session).

        Returns:
            MessagePage with items.
        """
        v1_id = _add_devin_prefix(session_id)
        resp = await self._request("GET", self._url(f"/sessions/{v1_id}"))
        data = resp.json()
        messages_data = data.get("messages", [])
        items = [
            Message(
                event_id=msg.get("event_id", ""),
                source=msg.get("type", ""),
                message=msg.get("message", ""),
                created_at=msg.get("created_at", 0),
            )
            for msg in messages_data
        ]
        return MessagePage(
            items=items,
            has_next_page=False,
            end_cursor=None,
        )

    # ── Playbook management ──

    async def create_playbook(self, title: str, body: str) -> str:
        """Create a new playbook. Returns the playbook_id."""
        resp = await self._request(
            "POST",
            self._url("/playbooks"),
            json={"title": title, "body": body},
        )
        return resp.json()["playbook_id"]

    async def list_playbooks(self) -> list[Playbook]:
        """List all playbooks in the organization."""
        resp = await self._request("GET", self._url("/playbooks"))
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
            self._url(f"/playbooks/{playbook_id}"),
            json={"title": title, "body": body},
        )

    # ── Internal helpers ──

    @staticmethod
    def _parse_session(data: dict) -> DevinSession:
        """Parse a v1 session response into a DevinSession.

        v1 differences from v3:
        - session_id has 'devin-' prefix (stripped here for consistency)
        - created_at/updated_at are ISO strings (stored as-is)
        - url may not be present in create response (constructed from session_id)
        - pull_request is a single dict or null (not a list)
        - v1 returns both 'status' (uses v3-compatible names like 'running',
          'exit') and 'status_enum' (v1-native names like 'working', 'finished',
          'blocked'). We read 'status' first; if absent, we fall back to
          'status_enum' with a mapping to v3-style names.
        """
        raw_id = data.get("session_id", "")
        session_id = _strip_devin_prefix(raw_id)

        # v1 create response may not include url; construct it
        url = data.get("url", "")
        if not url and session_id:
            url = f"https://app.devin.ai/sessions/{session_id}"

        # v1 returns 'status' with v3-compatible values (running, exit, new, etc.)
        # and 'status_enum' with v1-native values (working, finished, blocked, etc.).
        # Prefer 'status'; fall back to 'status_enum' with mapping if needed.
        status = data.get("status", "")
        if not status:
            raw_status = data.get("status_enum", "new")
            _v1_to_v3_status = {
                "working": "running",
                "blocked": "suspended",
                "finished": "exit",
                "expired": "exit",
            }
            status = _v1_to_v3_status.get(raw_status, raw_status)

        # v1 pull_request is singular (dict or null), not a list
        pr_data = data.get("pull_request")
        pull_requests: list[SessionPullRequest] = []
        if pr_data and isinstance(pr_data, dict):
            pull_requests = [
                SessionPullRequest(
                    pr_url=pr_data.get("pr_url", pr_data.get("url", "")),
                    pr_state=pr_data.get("pr_state", pr_data.get("state", "")),
                )
            ]

        return DevinSession(
            session_id=session_id,
            url=url,
            status=status,
            acus_consumed=data.get("acus_consumed") or 0.0,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            tags=data.get("tags", []),
            pull_requests=pull_requests,
        )
