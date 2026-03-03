"""Tests for orchestrator/devin_client.py — v1 API client."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from orchestrator.devin_client import DevinClient, _add_devin_prefix, _strip_devin_prefix

API_KEY = "apk_test_key"
ORG_ID = "org-test123"
V1_BASE = "https://api.devin.ai/v1"


@pytest.fixture
def client() -> DevinClient:
    return DevinClient(api_key=API_KEY, org_id=ORG_ID)


# ── Prefix helpers ──


def test_strip_devin_prefix() -> None:
    assert _strip_devin_prefix("devin-abc123") == "abc123"
    assert _strip_devin_prefix("abc123") == "abc123"
    assert _strip_devin_prefix("") == ""


def test_add_devin_prefix() -> None:
    assert _add_devin_prefix("abc123") == "devin-abc123"
    assert _add_devin_prefix("devin-abc123") == "devin-abc123"


# ── Session lifecycle ──


@pytest.mark.asyncio
async def test_create_session(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions",
        method="POST",
        json={
            "session_id": "devin-sess001",
            "status": "new",
            "tags": ["backlog-auto", "issue:42", "stage:triage"],
        },
    )

    session = await client.create_session(
        prompt="Triage issue #42",
        tags=["backlog-auto", "issue:42", "stage:triage"],
    )
    # devin- prefix should be stripped
    assert session.session_id == "sess001"
    assert session.status == "new"
    assert "backlog-auto" in session.tags
    # url should be constructed since v1 create doesn't return it
    assert session.url == "https://app.devin.ai/sessions/sess001"


@pytest.mark.asyncio
async def test_create_session_with_playbook(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions",
        method="POST",
        json={
            "session_id": "devin-sess002",
            "status": "new",
            "tags": ["backlog-auto", "issue:10"],
        },
    )

    session = await client.create_session(
        prompt="Triage issue #10",
        playbook_id="pb-triage-001",
        tags=["backlog-auto", "issue:10"],
        max_acu_limit=8,
    )
    assert session.session_id == "sess002"
    request = httpx_mock.get_requests()[-1]
    import json

    body = json.loads(request.content)
    assert body["playbook_id"] == "pb-triage-001"
    assert body["max_acu_limit"] == 8


@pytest.mark.asyncio
async def test_get_session(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    # v1 expects devin- prefix in URL
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions/devin-sess001",
        json={
            "session_id": "devin-sess001",
            "url": "https://app.devin.ai/sessions/sess001",
            "status": "running",
            "acus_consumed": 2.5,
            "tags": ["backlog-auto"],
        },
    )

    # Client accepts ID without prefix and adds it
    session = await client.get_session("sess001")
    assert session.session_id == "sess001"
    assert session.status == "running"
    assert session.acus_consumed == 2.5


@pytest.mark.asyncio
async def test_send_message(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    # v1 uses /message (singular)
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions/devin-sess001/message",
        method="POST",
        json={"ok": True},
    )

    await client.send_message("sess001", "Please check the test suite")
    request = httpx_mock.get_requests()[-1]
    import json

    body = json.loads(request.content)
    assert body["message"] == "Please check the test suite"


@pytest.mark.asyncio
async def test_terminate_session(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions/devin-sess001",
        method="DELETE",
        status_code=204,
    )

    await client.terminate_session("sess001")
    request = httpx_mock.get_requests()[-1]
    assert request.method == "DELETE"
    assert "devin-sess001" in str(request.url)


# ── Query helpers ──


@pytest.mark.asyncio
async def test_get_sessions_for_issue(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    # v1 uses server-side tag filtering; response key is "sessions"
    httpx_mock.add_response(
        url=httpx.URL(
            f"{V1_BASE}/sessions",
            params={"tags": "backlog-auto,issue:42", "limit": "100"},
        ),
        json={
            "sessions": [
                {
                    "session_id": "devin-sess001",
                    "status": "running",
                    "tags": ["backlog-auto", "issue:42"],
                },
                {
                    "session_id": "devin-sess002",
                    "status": "exit",
                    "tags": ["backlog-auto", "issue:42"],
                },
            ],
        },
    )

    sessions = await client.get_sessions_for_issue(42)
    assert len(sessions) == 2
    assert sessions[0].session_id == "sess001"
    assert sessions[0].status == "running"
    assert sessions[1].session_id == "sess002"


@pytest.mark.asyncio
async def test_get_active_session(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(
            f"{V1_BASE}/sessions",
            params={"tags": "backlog-auto,issue:42", "limit": "100"},
        ),
        json={
            "sessions": [
                {
                    "session_id": "devin-sess001",
                    "status": "running",
                    "tags": ["backlog-auto", "issue:42"],
                },
                {
                    "session_id": "devin-sess002",
                    "status": "exit",
                    "tags": ["backlog-auto", "issue:42"],
                },
            ],
        },
    )

    active = await client.get_active_session_for_issue(42)
    assert active is not None
    assert active.session_id == "sess001"


@pytest.mark.asyncio
async def test_get_active_session_none(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(
            f"{V1_BASE}/sessions",
            params={"tags": "backlog-auto,issue:42", "limit": "100"},
        ),
        json={
            "sessions": [
                {
                    "session_id": "devin-sess002",
                    "status": "exit",
                    "tags": ["backlog-auto", "issue:42"],
                },
            ],
        },
    )

    active = await client.get_active_session_for_issue(42)
    assert active is None


# ── Message polling ──


@pytest.mark.asyncio
async def test_list_messages(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    # v1 list_messages fetches GET /sessions/{id} and extracts messages
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions/devin-sess001",
        json={
            "session_id": "devin-sess001",
            "status": "running",
            "messages": [
                {
                    "event_id": "evt-001",
                    "type": "devin",
                    "message": "Starting triage...",
                    "created_at": 1700000000,
                },
            ],
        },
    )

    page = await client.list_messages("sess001")
    assert len(page.items) == 1
    assert page.items[0].source == "devin"
    assert page.items[0].message == "Starting triage..."
    assert page.has_next_page is False


@pytest.mark.asyncio
async def test_list_messages_empty(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions/devin-sess001",
        json={
            "session_id": "devin-sess001",
            "status": "new",
        },
    )

    page = await client.list_messages("sess001")
    assert len(page.items) == 0
    assert page.has_next_page is False
    assert page.end_cursor is None


# ── Playbook management ──


@pytest.mark.asyncio
async def test_create_playbook(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V1_BASE}/playbooks",
        method="POST",
        json={"playbook_id": "pb-001"},
    )

    playbook_id = await client.create_playbook("Triage", "# Triage instructions")
    assert playbook_id == "pb-001"


# ── Parse session: v1 response shapes ──


def test_parse_session_with_pull_request() -> None:
    data = {
        "session_id": "devin-abc123",
        "status": "finished",
        "pull_request": {
            "url": "https://github.com/org/repo/pull/1",
            "state": "open",
        },
    }
    session = DevinClient._parse_session(data)
    assert session.session_id == "abc123"
    assert len(session.pull_requests) == 1
    assert session.pull_requests[0].pr_url == "https://github.com/org/repo/pull/1"
    assert session.pull_requests[0].pr_state == "open"


def test_parse_session_no_pull_request() -> None:
    data = {
        "session_id": "devin-abc123",
        "status": "running",
        "pull_request": None,
    }
    session = DevinClient._parse_session(data)
    assert session.pull_requests == []


def test_parse_session_url_constructed() -> None:
    data = {
        "session_id": "devin-abc123",
        "status": "new",
    }
    session = DevinClient._parse_session(data)
    assert session.url == "https://app.devin.ai/sessions/abc123"


def test_parse_session_status_enum_fallback() -> None:
    """When 'status' is absent, fall back to 'status_enum' with v1→v3 mapping."""
    data = {
        "session_id": "devin-abc123",
        "status_enum": "working",
    }
    session = DevinClient._parse_session(data)
    assert session.status == "running"


def test_parse_session_status_enum_finished() -> None:
    """status_enum 'finished' maps to 'exit'."""
    data = {
        "session_id": "devin-abc123",
        "status_enum": "finished",
    }
    session = DevinClient._parse_session(data)
    assert session.status == "exit"


def test_parse_session_prefers_status_over_status_enum() -> None:
    """When both 'status' and 'status_enum' are present, 'status' wins."""
    data = {
        "session_id": "devin-abc123",
        "status": "running",
        "status_enum": "blocked",
    }
    session = DevinClient._parse_session(data)
    assert session.status == "running"


# ── Rate limit retry ──


@pytest.mark.asyncio
async def test_rate_limit_retry(client: DevinClient, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch) -> None:
    import orchestrator.devin_client as dc

    monkeypatch.setattr(dc, "_INITIAL_BACKOFF_SECONDS", 0.01)

    # First call returns 429, second returns success
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions/devin-sess001",
        status_code=429,
    )
    httpx_mock.add_response(
        url=f"{V1_BASE}/sessions/devin-sess001",
        json={
            "session_id": "devin-sess001",
            "status": "running",
        },
    )

    session = await client.get_session("sess001")
    assert session.session_id == "sess001"
    assert len(httpx_mock.get_requests()) == 2
