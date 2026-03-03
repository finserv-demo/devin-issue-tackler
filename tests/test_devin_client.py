import httpx
import pytest
from pytest_httpx import HTTPXMock

from orchestrator.devin_client import DevinClient

API_KEY = "cog_test_key"
ORG_ID = "org-test123"
V3_BASE = f"https://api.devin.ai/v3/organizations/{ORG_ID}"


@pytest.fixture
def client() -> DevinClient:
    return DevinClient(api_key=API_KEY, org_id=ORG_ID)


# ── Session lifecycle ──


@pytest.mark.asyncio
async def test_create_session(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V3_BASE}/sessions",
        method="POST",
        json={
            "session_id": "sess-001",
            "url": "https://app.devin.ai/sessions/sess-001",
            "status": "new",
            "tags": ["backlog-auto", "issue:42", "stage:triage"],
        },
    )

    session = await client.create_session(
        prompt="Triage issue #42",
        tags=["backlog-auto", "issue:42", "stage:triage"],
    )
    assert session.session_id == "sess-001"
    assert session.status == "new"
    assert "backlog-auto" in session.tags


@pytest.mark.asyncio
async def test_create_session_with_playbook(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V3_BASE}/sessions",
        method="POST",
        json={
            "session_id": "sess-002",
            "url": "https://app.devin.ai/sessions/sess-002",
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
    assert session.session_id == "sess-002"
    request = httpx_mock.get_requests()[-1]
    import json

    body = json.loads(request.content)
    assert body["playbook_id"] == "pb-triage-001"
    assert body["max_acu_limit"] == 8


@pytest.mark.asyncio
async def test_get_session(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V3_BASE}/sessions/sess-001",
        json={
            "session_id": "sess-001",
            "url": "https://app.devin.ai/sessions/sess-001",
            "status": "running",
            "acus_consumed": 2.5,
            "tags": ["backlog-auto"],
        },
    )

    session = await client.get_session("sess-001")
    assert session.session_id == "sess-001"
    assert session.status == "running"
    assert session.acus_consumed == 2.5


@pytest.mark.asyncio
async def test_send_message(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V3_BASE}/sessions/sess-001/messages",
        method="POST",
        json={"ok": True},
    )

    await client.send_message("sess-001", "Please check the test suite")
    request = httpx_mock.get_requests()[-1]
    import json

    body = json.loads(request.content)
    assert body["message"] == "Please check the test suite"


@pytest.mark.asyncio
async def test_terminate_session(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V3_BASE}/sessions/sess-001",
        method="DELETE",
        status_code=204,
    )

    await client.terminate_session("sess-001")
    request = httpx_mock.get_requests()[-1]
    assert request.method == "DELETE"


# ── Query helpers ──


@pytest.mark.asyncio
async def test_get_sessions_for_issue(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(f"{V3_BASE}/sessions", params={"first": "100"}),
        json={
            "items": [
                {
                    "session_id": "sess-001",
                    "url": "",
                    "status": "running",
                    "tags": ["backlog-auto", "issue:42"],
                },
                {
                    "session_id": "sess-002",
                    "url": "",
                    "status": "exit",
                    "tags": ["backlog-auto", "issue:42"],
                },
                {
                    "session_id": "sess-003",
                    "url": "",
                    "status": "running",
                    "tags": ["backlog-auto", "issue:99"],
                },
            ],
            "has_next_page": False,
            "end_cursor": None,
        },
    )

    sessions = await client.get_sessions_for_issue(42)
    # Should filter to only sessions with both backlog-auto and issue:42 tags
    assert len(sessions) == 2
    assert sessions[0].session_id == "sess-001"
    assert sessions[0].status == "running"
    # sess-003 (issue:99) should be excluded
    assert all(s.session_id != "sess-003" for s in sessions)


@pytest.mark.asyncio
async def test_get_active_session(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(f"{V3_BASE}/sessions", params={"first": "100"}),
        json={
            "items": [
                {
                    "session_id": "sess-001",
                    "url": "",
                    "status": "running",
                    "tags": ["backlog-auto", "issue:42"],
                },
                {
                    "session_id": "sess-002",
                    "url": "",
                    "status": "exit",
                    "tags": ["backlog-auto", "issue:42"],
                },
            ],
            "has_next_page": False,
            "end_cursor": None,
        },
    )

    active = await client.get_active_session_for_issue(42)
    assert active is not None
    assert active.session_id == "sess-001"


@pytest.mark.asyncio
async def test_get_active_session_none(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(f"{V3_BASE}/sessions", params={"first": "100"}),
        json={
            "items": [
                {
                    "session_id": "sess-002",
                    "url": "",
                    "status": "exit",
                    "tags": ["backlog-auto", "issue:42"],
                },
            ],
            "has_next_page": False,
            "end_cursor": None,
        },
    )

    active = await client.get_active_session_for_issue(42)
    assert active is None


# ── Message polling ──


@pytest.mark.asyncio
async def test_list_messages(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(
            f"{V3_BASE}/sessions/sess-001/messages",
            params={"first": "100"},
        ),
        json={
            "items": [
                {
                    "event_id": "evt-001",
                    "source": "devin",
                    "message": "Starting triage...",
                    "created_at": 1700000000,
                },
            ],
            "has_next_page": False,
            "end_cursor": None,
        },
    )

    page = await client.list_messages("sess-001")
    assert len(page.items) == 1
    assert page.items[0].source == "devin"
    assert page.items[0].message == "Starting triage..."
    assert page.has_next_page is False


@pytest.mark.asyncio
async def test_list_messages_with_cursor(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(
            f"{V3_BASE}/sessions/sess-001/messages",
            params={"first": "100", "after": "cursor-prev"},
        ),
        json={
            "items": [
                {
                    "event_id": "evt-002",
                    "source": "user",
                    "message": "/proceed",
                    "created_at": 1700001000,
                },
            ],
            "has_next_page": True,
            "end_cursor": "cursor-abc",
        },
    )

    page = await client.list_messages("sess-001", after="cursor-prev")
    assert len(page.items) == 1
    assert page.has_next_page is True
    assert page.end_cursor == "cursor-abc"


# ── Playbook management ──


@pytest.mark.asyncio
async def test_create_playbook(client: DevinClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{V3_BASE}/playbooks",
        method="POST",
        json={"playbook_id": "pb-001"},
    )

    playbook_id = await client.create_playbook("Triage", "# Triage instructions")
    assert playbook_id == "pb-001"


# ── Rate limit retry ──


@pytest.mark.asyncio
async def test_rate_limit_retry(client: DevinClient, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Client should retry on 429 with exponential backoff."""
    import orchestrator.devin_client as dc

    monkeypatch.setattr(dc, "_INITIAL_BACKOFF_SECONDS", 0.01)

    # First call returns 429, second returns success
    httpx_mock.add_response(
        url=f"{V3_BASE}/sessions/sess-001",
        status_code=429,
    )
    httpx_mock.add_response(
        url=f"{V3_BASE}/sessions/sess-001",
        json={
            "session_id": "sess-001",
            "status": "running",
        },
    )

    session = await client.get_session("sess-001")
    assert session.session_id == "sess-001"
    assert len(httpx_mock.get_requests()) == 2
