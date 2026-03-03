"""Tests for scripts/devin_api.py — the GitHub Actions Devin API helper."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from orchestrator.schemas.devin import DevinSession

# Add scripts parent to path so we can import the module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.devin_api import (  # noqa: I001
    _extract_label_names,
    _format_comments,
    build_implement_prompt,
    build_triage_prompt,
    cmd_check_active_session,
    cmd_create_session,
    cmd_forward_comment,
    cmd_terminate_active,
)


# ── Prompt building ──


def test_build_triage_prompt_basic() -> None:
    context = {
        "title": "Fix login bug",
        "body": "Login page is broken when clicking submit.",
        "labels": [{"name": "bug"}, {"name": "devin:triage"}],
        "comments": [],
    }
    prompt = build_triage_prompt(42, "finserv-demo/finserv", context)

    assert "Triage GitHub issue #42" in prompt
    assert "Fix login bug" in prompt
    assert "Login page is broken" in prompt
    assert "bug, devin:triage" in prompt
    assert "finserv-demo/finserv" in prompt
    assert "https://github.com/finserv-demo/finserv/issues/42" in prompt
    assert "Existing Comments" not in prompt


def test_build_triage_prompt_with_comments() -> None:
    context = {
        "title": "Add dark mode",
        "body": "Please add dark mode support.",
        "labels": [],
        "comments": [
            {"author": {"login": "emily-ross"}, "body": "This would be great!"},
            {"author": {"login": "octocat"}, "body": "Agreed, +1"},
        ],
    }
    prompt = build_triage_prompt(10, "finserv-demo/finserv", context)

    assert "Existing Comments" in prompt
    assert "@emily-ross" in prompt
    assert "This would be great!" in prompt
    assert "@octocat" in prompt
    assert "Agreed, +1" in prompt


def test_build_triage_prompt_with_none_body() -> None:
    context = {"title": "Empty body issue", "body": None, "labels": [], "comments": []}
    prompt = build_triage_prompt(1, "org/repo", context)

    assert "Empty body issue" in prompt
    assert "**Labels:** none" in prompt


def test_build_implement_prompt_basic() -> None:
    context = {
        "title": "Fix login bug",
        "body": "Login page is broken.",
        "labels": [{"name": "devin:implement"}, {"name": "devin:green"}],
        "comments": [
            {"author": {"login": "devin-ai-integration[bot]"}, "body": "## Triage Analysis\nSmall fix needed."},
        ],
    }
    prompt = build_implement_prompt(42, "finserv-demo/finserv", context)

    assert "Implement a fix for GitHub issue #42" in prompt
    assert "Fix login bug" in prompt
    assert "Comments (includes triage analysis" in prompt
    assert "Triage Analysis" in prompt


def test_build_implement_prompt_no_comments() -> None:
    context = {
        "title": "Simple fix",
        "body": "Fix typo.",
        "labels": [],
        "comments": [],
    }
    prompt = build_implement_prompt(5, "org/repo", context)

    assert "Implement a fix" in prompt
    assert "Comments" not in prompt


# ── Helper functions ──


def test_extract_label_names_from_dicts() -> None:
    labels = [{"name": "bug"}, {"name": "devin:triage"}]
    assert _extract_label_names(labels) == ["bug", "devin:triage"]


def test_extract_label_names_from_strings() -> None:
    labels = ["bug", "devin:triage"]
    assert _extract_label_names(labels) == ["bug", "devin:triage"]


def test_extract_label_names_empty() -> None:
    assert _extract_label_names([]) == []


def test_format_comments_with_dict_author() -> None:
    comments = [
        {"author": {"login": "emily-ross"}, "body": "Looks good"},
        {"author": {"login": "octocat"}, "body": "Approved"},
    ]
    result = _format_comments(comments)
    assert "@emily-ross" in result
    assert "Looks good" in result
    assert "@octocat" in result
    assert "Approved" in result


def test_format_comments_with_string_author() -> None:
    comments = [{"author": "emily-ross", "body": "test"}]
    result = _format_comments(comments)
    assert "emily-ross" in result


def test_format_comments_empty() -> None:
    assert _format_comments([]) == ""


def test_format_comments_missing_author() -> None:
    comments = [{"author": {}, "body": "anonymous comment"}]
    result = _format_comments(comments)
    assert "unknown" in result
    assert "anonymous comment" in result


# ── cmd_create_session ──


@pytest.fixture
def mock_devin_session() -> DevinSession:
    return DevinSession(
        session_id="sess-test-001",
        url="https://app.devin.ai/sessions/sess-test-001",
        status="new",
        tags=["backlog-auto", "issue:42", "stage:triage"],
    )


@pytest.fixture
def context_file(tmp_path: Path) -> Path:
    context = {
        "title": "Test Issue",
        "body": "Test body",
        "labels": [{"name": "bug"}],
        "comments": [],
    }
    filepath = tmp_path / "context.json"
    filepath.write_text(json.dumps(context))
    return filepath


@pytest.fixture
def github_output_file(tmp_path: Path) -> Path:
    filepath = tmp_path / "github_output.txt"
    filepath.write_text("")
    return filepath


class FakeArgs:
    """Fake argparse.Namespace for testing."""

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.mark.asyncio
async def test_cmd_create_session_triage(
    mock_devin_session: DevinSession,
    context_file: Path,
    github_output_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")
    monkeypatch.setenv("TRIAGE_PLAYBOOK_ID", "pb-triage-001")
    monkeypatch.setenv("ACU_LIMIT_TRIAGE", "8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output_file))

    mock_client = AsyncMock()
    mock_client.create_session.return_value = mock_devin_session

    args = FakeArgs(
        stage="triage",
        issue=42,
        repo="finserv-demo/finserv",
        context_file=str(context_file),
    )

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_create_session(args)

    # Verify create_session was called with correct args
    mock_client.create_session.assert_called_once()
    call_kwargs = mock_client.create_session.call_args
    assert call_kwargs.kwargs["playbook_id"] == "pb-triage-001"
    assert call_kwargs.kwargs["max_acu_limit"] == 8
    assert "backlog-auto" in call_kwargs.kwargs["tags"]
    assert "issue:42" in call_kwargs.kwargs["tags"]
    assert "stage:triage" in call_kwargs.kwargs["tags"]
    assert "Triage GitHub issue #42" in call_kwargs.kwargs["prompt"]

    # Verify GITHUB_OUTPUT was written
    output_content = github_output_file.read_text()
    assert "session_id=sess-test-001" in output_content
    assert "session_url=https://app.devin.ai/sessions/sess-test-001" in output_content


@pytest.mark.asyncio
async def test_cmd_create_session_implement(
    context_file: Path,
    github_output_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")
    monkeypatch.setenv("IMPLEMENT_PLAYBOOK_ID", "pb-impl-001")
    monkeypatch.setenv("ACU_LIMIT_IMPLEMENT", "50")
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output_file))

    implement_session = DevinSession(
        session_id="sess-impl-001",
        url="https://app.devin.ai/sessions/sess-impl-001",
        status="new",
    )
    mock_client = AsyncMock()
    mock_client.create_session.return_value = implement_session

    args = FakeArgs(
        stage="implement",
        issue=42,
        repo="finserv-demo/finserv",
        context_file=str(context_file),
    )

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_create_session(args)

    call_kwargs = mock_client.create_session.call_args
    assert call_kwargs.kwargs["playbook_id"] == "pb-impl-001"
    assert call_kwargs.kwargs["max_acu_limit"] == 50
    assert "stage:implement" in call_kwargs.kwargs["tags"]
    assert "Implement a fix for GitHub issue #42" in call_kwargs.kwargs["prompt"]


@pytest.mark.asyncio
async def test_cmd_create_session_no_playbook(
    context_file: Path,
    github_output_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When playbook ID env var is empty, playbook_id should be None."""
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")
    monkeypatch.setenv("TRIAGE_PLAYBOOK_ID", "")
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output_file))

    mock_client = AsyncMock()
    mock_client.create_session.return_value = DevinSession(session_id="s1", url="u1", status="new")

    args = FakeArgs(stage="triage", issue=1, repo="org/repo", context_file=str(context_file))

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_create_session(args)

    call_kwargs = mock_client.create_session.call_args
    assert call_kwargs.kwargs["playbook_id"] is None


# ── cmd_check_active_session ──


@pytest.mark.asyncio
async def test_cmd_check_active_session_found(
    github_output_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output_file))

    active_session = DevinSession(
        session_id="sess-active-001",
        url="https://app.devin.ai/sessions/sess-active-001",
        status="running",
    )
    mock_client = AsyncMock()
    mock_client.get_active_session_for_issue.return_value = active_session

    args = FakeArgs(issue=42)

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_check_active_session(args)

    mock_client.get_active_session_for_issue.assert_called_once_with(42)
    output_content = github_output_file.read_text()
    assert "has_active=true" in output_content
    assert "active_session_id=sess-active-001" in output_content
    assert "active_session_url=https://app.devin.ai/sessions/sess-active-001" in output_content


@pytest.mark.asyncio
async def test_cmd_check_active_session_not_found(
    github_output_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output_file))

    mock_client = AsyncMock()
    mock_client.get_active_session_for_issue.return_value = None

    args = FakeArgs(issue=42)

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_check_active_session(args)

    output_content = github_output_file.read_text()
    assert "has_active=false" in output_content
    assert "active_session_id" not in output_content


# ── cmd_terminate_active ──


@pytest.mark.asyncio
async def test_cmd_terminate_active_with_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """When an active session exists, terminate it."""
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")

    active_session = DevinSession(session_id="sess-active", url="", status="running")
    mock_client = AsyncMock()
    mock_client.get_active_session_for_issue.return_value = active_session

    args = FakeArgs(issue=42)

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_terminate_active(args)

    mock_client.get_active_session_for_issue.assert_called_once_with(42)
    mock_client.terminate_session.assert_called_once_with("sess-active")


@pytest.mark.asyncio
async def test_cmd_terminate_active_no_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")

    mock_client = AsyncMock()
    mock_client.get_active_session_for_issue.return_value = None

    args = FakeArgs(issue=42)

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_terminate_active(args)

    mock_client.terminate_session.assert_not_called()


# ── cmd_forward_comment ──


@pytest.mark.asyncio
async def test_cmd_forward_comment_with_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")

    body_file = tmp_path / "body.txt"
    body_file.write_text("Please also fix the dark mode toggle.")

    active_session = DevinSession(session_id="sess-active", url="", status="running")
    mock_client = AsyncMock()
    mock_client.get_active_session_for_issue.return_value = active_session

    args = FakeArgs(issue=42, author="emily-ross", body=None, body_file=str(body_file))

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_forward_comment(args)

    mock_client.send_message.assert_called_once()
    message = mock_client.send_message.call_args[0][1]
    assert "@emily-ross" in message
    assert "Please also fix the dark mode toggle." in message
    assert "#42" in message


@pytest.mark.asyncio
async def test_cmd_forward_comment_with_body_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")

    active_session = DevinSession(session_id="sess-active", url="", status="running")
    mock_client = AsyncMock()
    mock_client.get_active_session_for_issue.return_value = active_session

    args = FakeArgs(issue=10, author="octocat", body="Inline body text", body_file=None)

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_forward_comment(args)

    message = mock_client.send_message.call_args[0][1]
    assert "Inline body text" in message


@pytest.mark.asyncio
async def test_cmd_forward_comment_no_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVIN_API_KEY", "cog_test")
    monkeypatch.setenv("DEVIN_ORG_ID", "org-test")

    body_file = tmp_path / "body.txt"
    body_file.write_text("Hello")

    mock_client = AsyncMock()
    mock_client.get_active_session_for_issue.return_value = None

    args = FakeArgs(issue=42, author="octocat", body=None, body_file=str(body_file))

    with patch("scripts.devin_api.get_devin_client", return_value=mock_client):
        await cmd_forward_comment(args)

    mock_client.send_message.assert_not_called()
