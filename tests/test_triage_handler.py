"""Tests for the triage pipeline handler."""

from unittest.mock import AsyncMock

import pytest

from orchestrator.config import Settings
from orchestrator.context import build_triage_context
from orchestrator.handlers.triage import handle_triage
from orchestrator.schemas.devin import DevinSession
from orchestrator.schemas.github import GitHubComment, GitHubIssue


@pytest.fixture
def settings() -> Settings:
    return Settings(
        github_token="ghp_test",
        devin_api_key="cog_test",
        devin_org_id="org-test",
        triage_playbook_id="pb-triage-001",
        implement_playbook_id="pb-impl-001",
        acu_limit_triage=8,
        target_repo="finserv-demo/finserv",
    )


@pytest.fixture
def github() -> AsyncMock:
    mock = AsyncMock()
    mock.get_labels.return_value = ["bug"]
    mock.add_reaction.return_value = 999
    mock.get_issue.return_value = GitHubIssue(
        number=42,
        title="Fix login bug",
        body="Login page broken",
        labels=["bug", "devin:triage"],
        state="open",
        html_url="https://github.com/finserv-demo/finserv/issues/42",
    )
    mock.get_issue_comments.return_value = [
        GitHubComment(id=1, author="user1", body="I can reproduce this", created_at="2024-01-01T00:00:00Z"),
    ]
    return mock


@pytest.fixture
def devin() -> AsyncMock:
    mock = AsyncMock()
    mock.create_session.return_value = DevinSession(
        session_id="sess-001",
        url="https://app.devin.ai/sessions/sess-001",
        status="new",
        tags=["backlog-auto", "issue:42", "stage:triage"],
    )
    return mock


@pytest.mark.asyncio
async def test_handle_triage_creates_session(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Verifies Devin session created with correct tags."""
    await handle_triage(42, github, devin, settings)
    devin.create_session.assert_called_once()
    call_kwargs = devin.create_session.call_args.kwargs
    assert "backlog-auto" in call_kwargs["tags"]
    assert "issue:42" in call_kwargs["tags"]
    assert "stage:triage" in call_kwargs["tags"]


@pytest.mark.asyncio
async def test_handle_triage_adds_eyes_reaction(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Verifies eyes reaction added to issue."""
    await handle_triage(42, github, devin, settings)
    github.add_reaction.assert_called_once_with(42, "eyes")


@pytest.mark.asyncio
async def test_handle_triage_skips_opted_out(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """No session if devin:skip label present."""
    github.get_labels.return_value = ["bug", "devin:skip"]
    await handle_triage(42, github, devin, settings)
    devin.create_session.assert_not_called()
    github.add_reaction.assert_not_called()


@pytest.mark.asyncio
async def test_handle_triage_includes_playbook(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Session created with triage playbook_id."""
    await handle_triage(42, github, devin, settings)
    call_kwargs = devin.create_session.call_args.kwargs
    assert call_kwargs["playbook_id"] == "pb-triage-001"


@pytest.mark.asyncio
async def test_handle_triage_sets_acu_limit(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """ACU limit from settings."""
    await handle_triage(42, github, devin, settings)
    call_kwargs = devin.create_session.call_args.kwargs
    assert call_kwargs["max_acu_limit"] == 8


@pytest.mark.asyncio
async def test_handle_triage_tags(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Session has backlog-auto, issue:{n}, stage:triage, repo:... tags."""
    await handle_triage(42, github, devin, settings)
    call_kwargs = devin.create_session.call_args.kwargs
    tags = call_kwargs["tags"]
    assert "backlog-auto" in tags
    assert "issue:42" in tags
    assert "stage:triage" in tags
    assert "repo:finserv-demo/finserv" in tags


@pytest.mark.asyncio
async def test_build_triage_context(github: AsyncMock) -> None:
    """Context includes issue title, body, and comments."""
    context = await build_triage_context(42, github)
    assert "Fix login bug" in context
    assert "Login page broken" in context
    assert "I can reproduce this" in context


@pytest.mark.asyncio
async def test_build_triage_context_empty_body(github: AsyncMock) -> None:
    """Handles issues with no body."""
    github.get_issue.return_value = GitHubIssue(
        number=42,
        title="Empty issue",
        body=None,
        labels=[],
        state="open",
    )
    github.get_issue_comments.return_value = []
    context = await build_triage_context(42, github)
    assert "Empty issue" in context
    assert "_No description provided._" in context


@pytest.mark.asyncio
async def test_on_issue_opened_adds_triage_label() -> None:
    """Webhook handler adds label."""
    from orchestrator.webhooks import on_issue_opened

    github = AsyncMock()
    settings = Settings(github_token="ghp_test", devin_api_key="cog_test", devin_org_id="org-test")
    payload = {
        "issue": {
            "number": 42,
            "title": "Bug",
            "labels": [],
        }
    }
    await on_issue_opened(payload, github, settings)
    github.add_label.assert_called_once_with(42, "devin:triage")


@pytest.mark.asyncio
async def test_on_issue_opened_skip_label() -> None:
    """No label added if devin:skip present."""
    from orchestrator.webhooks import on_issue_opened

    github = AsyncMock()
    settings = Settings(github_token="ghp_test", devin_api_key="cog_test", devin_org_id="org-test")
    payload = {
        "issue": {
            "number": 42,
            "title": "Bug",
            "labels": [{"name": "devin:skip"}],
        }
    }
    await on_issue_opened(payload, github, settings)
    github.add_label.assert_not_called()
