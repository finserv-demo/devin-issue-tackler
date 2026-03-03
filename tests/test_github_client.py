import httpx
import pytest
from pytest_httpx import HTTPXMock

from orchestrator.github_client import GitHubClient

REPO = "finserv-demo/finserv"
TOKEN = "ghp_test_token"
BASE = "https://api.github.com/repos/finserv-demo/finserv"


@pytest.fixture
def client() -> GitHubClient:
    return GitHubClient(token=TOKEN, repo=REPO)


# ── Issue operations ──


@pytest.mark.asyncio
async def test_get_issue(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/issues/42",
        json={
            "number": 42,
            "title": "Fix login bug",
            "body": "Login page broken",
            "labels": [{"name": "bug"}, {"name": "devin:triage"}],
            "state": "open",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "html_url": "https://github.com/finserv-demo/finserv/issues/42",
        },
    )

    issue = await client.get_issue(42)
    assert issue.number == 42
    assert issue.title == "Fix login bug"
    assert issue.body == "Login page broken"
    assert issue.labels == ["bug", "devin:triage"]
    assert issue.state == "open"


@pytest.mark.asyncio
async def test_list_issues_with_label_filter(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(
            f"{BASE}/issues",
            params={"state": "open", "per_page": "100", "page": "1", "labels": "devin:triage"},
        ),
        json=[
            {
                "number": 1,
                "title": "Issue 1",
                "body": "body",
                "labels": [{"name": "devin:triage"}],
                "state": "open",
                "created_at": "",
                "updated_at": "",
                "html_url": "",
            },
        ],
    )

    issues = await client.list_issues(labels=["devin:triage"])
    assert len(issues) == 1
    assert issues[0].number == 1


@pytest.mark.asyncio
async def test_post_comment(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/comments",
        method="POST",
        json={
            "id": 100,
            "user": {"login": "devin-bot"},
            "body": "Triage complete.",
            "created_at": "2024-01-01T00:00:00Z",
        },
    )

    comment = await client.post_comment(42, "Triage complete.")
    assert comment.id == 100
    assert comment.author == "devin-bot"
    assert comment.body == "Triage complete."


# ── Label operations ──


@pytest.mark.asyncio
async def test_add_label(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/labels",
        method="POST",
        json=[{"name": "devin:triage"}],
    )

    await client.add_label(42, "devin:triage")
    request = httpx_mock.get_requests()[-1]
    assert request.method == "POST"


@pytest.mark.asyncio
async def test_remove_label(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/labels/devin:triage",
        method="DELETE",
        json=[],
    )

    await client.remove_label(42, "devin:triage")
    request = httpx_mock.get_requests()[-1]
    assert request.method == "DELETE"


@pytest.mark.asyncio
async def test_remove_label_not_found(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    """Removing a non-existent label should not raise."""
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/labels/devin:triage",
        method="DELETE",
        status_code=404,
    )

    # Should not raise
    await client.remove_label(42, "devin:triage")


@pytest.mark.asyncio
async def test_swap_label(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/labels/devin:triage",
        method="DELETE",
        json=[],
    )
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/labels",
        method="POST",
        json=[{"name": "devin:triaged"}],
    )

    await client.swap_label(42, "devin:triage", "devin:triaged")
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].method == "DELETE"
    assert requests[1].method == "POST"


@pytest.mark.asyncio
async def test_remove_all_devin_labels(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/labels",
        method="GET",
        json=[{"name": "bug"}, {"name": "devin:triage"}, {"name": "devin:green"}],
    )
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/labels/devin:triage",
        method="DELETE",
        json=[],
    )
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/labels/devin:green",
        method="DELETE",
        json=[],
    )

    await client.remove_all_devin_labels(42)
    requests = httpx_mock.get_requests()
    # 1 GET + 2 DELETEs (only devin: labels, not "bug")
    assert len(requests) == 3


@pytest.mark.asyncio
async def test_ensure_labels_exist(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(f"{BASE}/labels", params={"per_page": "100", "page": "1"}),
        method="GET",
        json=[{"name": "bug"}, {"name": "devin:triage"}],
    )
    httpx_mock.add_response(
        url=f"{BASE}/labels",
        method="POST",
        json={"name": "devin:triaged", "color": "0e8a16"},
    )

    await client.ensure_labels_exist({"devin:triage": "1d76db", "devin:triaged": "0e8a16"})
    requests = httpx_mock.get_requests()
    # 1 GET + 1 POST (only the missing label)
    assert len(requests) == 2
    assert requests[1].method == "POST"


# ── Reaction operations ──


@pytest.mark.asyncio
async def test_add_reaction_eyes(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/reactions",
        method="POST",
        json={"id": 999, "content": "eyes"},
    )

    reaction_id = await client.add_reaction(42, "eyes")
    assert reaction_id == 999
    request = httpx_mock.get_requests()[-1]
    assert b'"content":"eyes"' in request.content or b'"content": "eyes"' in request.content


@pytest.mark.asyncio
async def test_remove_reaction(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/issues/42/reactions/999",
        method="DELETE",
        status_code=204,
    )

    await client.remove_reaction(42, 999)
    request = httpx_mock.get_requests()[-1]
    assert request.method == "DELETE"


# ── Timeline events ──


@pytest.mark.asyncio
async def test_get_timeline_events(client: GitHubClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL(f"{BASE}/issues/42/timeline", params={"per_page": "100", "page": "1"}),
        json=[
            {
                "event": "labeled",
                "label": {"name": "devin:triage"},
                "created_at": "2024-01-01T00:00:00Z",
                "actor": {"login": "emily-ross"},
            },
            {
                "event": "commented",
                "created_at": "2024-01-01T01:00:00Z",
                "actor": {"login": "devin-bot"},
            },
        ],
    )

    events = await client.get_timeline_events(42)
    assert len(events) == 2
    assert events[0].event == "labeled"
    assert events[0].label == "devin:triage"
    assert events[0].actor == "emily-ross"
    assert events[1].event == "commented"
    assert events[1].label is None
