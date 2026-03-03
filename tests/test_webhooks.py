"""Tests for the webhook receiver and event router."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from orchestrator.main import app

WEBHOOK_SECRET = "test-secret-123"


def _sign(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _headers(payload: bytes, event: str = "issues") -> dict[str, str]:
    """Build webhook headers with correct signature."""
    return {
        "X-Hub-Signature-256": _sign(payload),
        "X-GitHub-Event": event,
        "Content-Type": "application/json",
    }


@pytest.fixture
def _mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for Settings."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_valid_signature_accepted() -> None:
    """200 response with valid HMAC."""
    payload = json.dumps({"action": "opened", "issue": {"number": 1, "title": "Test", "labels": []}}).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("orchestrator.webhooks.on_issue_opened", new_callable=AsyncMock):
            resp = await client.post("/webhooks/github", content=payload, headers=_headers(payload))
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_invalid_signature_rejected() -> None:
    """401 response with bad HMAC."""
    payload = json.dumps({"action": "opened", "issue": {"number": 1}}).encode()
    headers = {
        "X-Hub-Signature-256": "sha256=bad_signature",
        "X-GitHub-Event": "issues",
        "Content-Type": "application/json",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/webhooks/github", content=payload, headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_missing_signature_rejected() -> None:
    """422 response (missing header)."""
    payload = json.dumps({"action": "opened"}).encode()
    headers = {
        "X-GitHub-Event": "issues",
        "Content-Type": "application/json",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/webhooks/github", content=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_issues_opened_dispatched() -> None:
    """Verify on_issue_opened called with correct payload."""
    payload_dict = {"action": "opened", "issue": {"number": 42, "title": "Bug", "labels": []}}
    payload = json.dumps(payload_dict).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("orchestrator.webhooks.on_issue_opened", new_callable=AsyncMock) as mock_handler:
            resp = await client.post("/webhooks/github", content=payload, headers=_headers(payload))
    assert resp.status_code == 200
    mock_handler.assert_called_once()
    call_args = mock_handler.call_args
    assert call_args[0][0] == payload_dict


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_issues_labeled_dispatched() -> None:
    """Verify on_issue_labeled called."""
    payload_dict = {
        "action": "labeled",
        "issue": {"number": 42, "labels": [{"name": "devin:triage"}]},
        "label": {"name": "devin:triage"},
    }
    payload = json.dumps(payload_dict).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("orchestrator.webhooks.on_issue_labeled", new_callable=AsyncMock) as mock_handler:
            resp = await client.post("/webhooks/github", content=payload, headers=_headers(payload))
    assert resp.status_code == 200
    mock_handler.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_issue_comment_created_dispatched() -> None:
    """Verify on_issue_comment called."""
    payload_dict = {
        "action": "created",
        "issue": {"number": 42, "labels": []},
        "comment": {"user": {"login": "emily-ross"}, "body": "/proceed"},
    }
    payload = json.dumps(payload_dict).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("orchestrator.webhooks.on_issue_comment", new_callable=AsyncMock) as mock_handler:
            resp = await client.post(
                "/webhooks/github",
                content=payload,
                headers=_headers(payload, event="issue_comment"),
            )
    assert resp.status_code == 200
    mock_handler.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_issues_closed_dispatched() -> None:
    """Verify on_issue_closed called."""
    payload_dict = {"action": "closed", "issue": {"number": 42, "labels": []}}
    payload = json.dumps(payload_dict).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("orchestrator.webhooks.on_issue_closed", new_callable=AsyncMock) as mock_handler:
            resp = await client.post("/webhooks/github", content=payload, headers=_headers(payload))
    assert resp.status_code == 200
    mock_handler.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_unknown_event_ignored() -> None:
    """Returns 200 without error for push events."""
    payload = json.dumps({"ref": "refs/heads/main"}).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhooks/github",
            content=payload,
            headers=_headers(payload, event="push"),
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_issue_comment_deleted_ignored() -> None:
    """Only 'created' action triggers handler."""
    payload_dict = {
        "action": "deleted",
        "issue": {"number": 42, "labels": []},
        "comment": {"user": {"login": "emily-ross"}, "body": "old comment"},
    }
    payload = json.dumps(payload_dict).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("orchestrator.webhooks.on_issue_comment", new_callable=AsyncMock) as mock_handler:
            resp = await client.post(
                "/webhooks/github",
                content=payload,
                headers=_headers(payload, event="issue_comment"),
            )
    assert resp.status_code == 200
    mock_handler.assert_not_called()
