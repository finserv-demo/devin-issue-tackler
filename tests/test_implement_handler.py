"""Tests for the implementation pipeline handler."""

from unittest.mock import AsyncMock

import pytest

from orchestrator.config import Settings
from orchestrator.context import build_implement_context
from orchestrator.handlers.implement import handle_implement
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
        acu_limit_implement=50,
        target_repo="finserv-demo/finserv",
    )


@pytest.fixture
def github() -> AsyncMock:
    mock = AsyncMock()
    mock.add_reaction.return_value = 888
    mock.get_issue.return_value = GitHubIssue(
        number=42,
        title="Fix login bug",
        body="Login page broken",
        labels=["bug", "devin:implement"],
        state="open",
        html_url="https://github.com/finserv-demo/finserv/issues/42",
    )
    mock.get_issue_comments.return_value = [
        GitHubComment(
            id=1,
            author="devin-ai-integration[bot]",
            body="## Triage Analysis\nSmall fix in auth service.",
            created_at="2024-01-01T00:00:00Z",
        ),
        GitHubComment(
            id=2,
            author="emily-ross",
            body="/proceed looks good to me",
            created_at="2024-01-02T00:00:00Z",
        ),
    ]
    return mock


@pytest.fixture
def devin() -> AsyncMock:
    mock = AsyncMock()
    mock.create_session.return_value = DevinSession(
        session_id="sess-impl-001",
        url="https://app.devin.ai/sessions/sess-impl-001",
        status="new",
        tags=["backlog-auto", "issue:42", "stage:implement"],
    )
    return mock


@pytest.mark.asyncio
async def test_handle_implement_creates_session(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Devin session created with correct tags."""
    await handle_implement(42, github, devin, settings)
    devin.create_session.assert_called_once()
    call_kwargs = devin.create_session.call_args.kwargs
    assert "backlog-auto" in call_kwargs["tags"]
    assert "issue:42" in call_kwargs["tags"]
    assert "stage:implement" in call_kwargs["tags"]


@pytest.mark.asyncio
async def test_handle_implement_adds_eyes_reaction(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Eyes reaction added to issue."""
    await handle_implement(42, github, devin, settings)
    github.add_reaction.assert_called_once_with(42, "eyes")


@pytest.mark.asyncio
async def test_handle_implement_includes_playbook(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Session created with implement playbook_id."""
    await handle_implement(42, github, devin, settings)
    call_kwargs = devin.create_session.call_args.kwargs
    assert call_kwargs["playbook_id"] == "pb-impl-001"


@pytest.mark.asyncio
async def test_handle_implement_sets_acu_limit(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Uses implement ACU limit (not triage)."""
    await handle_implement(42, github, devin, settings)
    call_kwargs = devin.create_session.call_args.kwargs
    assert call_kwargs["max_acu_limit"] == 50


@pytest.mark.asyncio
async def test_handle_implement_tags(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Session has backlog-auto, issue:{n}, stage:implement, repo:... tags."""
    await handle_implement(42, github, devin, settings)
    call_kwargs = devin.create_session.call_args.kwargs
    tags = call_kwargs["tags"]
    assert "backlog-auto" in tags
    assert "issue:42" in tags
    assert "stage:implement" in tags
    assert "repo:finserv-demo/finserv" in tags


@pytest.mark.asyncio
async def test_build_implement_context_includes_triage(github: AsyncMock) -> None:
    """Context includes triage analysis comment."""
    context = await build_implement_context(42, github)
    assert "Triage Analysis" in context
    assert "Small fix in auth service." in context


@pytest.mark.asyncio
async def test_build_implement_context_includes_human_feedback(github: AsyncMock) -> None:
    """Context includes all human comments."""
    context = await build_implement_context(42, github)
    assert "emily-ross" in context
    assert "/proceed looks good to me" in context
