"""Tests for the slash command handler."""

from unittest.mock import AsyncMock

import pytest

from orchestrator.config import Settings
from orchestrator.handlers.commands import (
    handle_comment,
    parse_slash_command,
)
from orchestrator.schemas.devin import DevinSession


@pytest.fixture
def settings() -> Settings:
    return Settings(
        github_token="ghp_test",
        devin_api_key="cog_test",
        devin_org_id="org-test",
    )


@pytest.fixture
def github() -> AsyncMock:
    mock = AsyncMock()
    mock.get_labels.return_value = ["bug", "devin:triaged"]
    mock.remove_all_devin_labels.return_value = None
    mock.swap_label.return_value = None
    mock.add_label.return_value = None
    mock.close_issue.return_value = None
    return mock


@pytest.fixture
def devin() -> AsyncMock:
    mock = AsyncMock()
    mock.get_active_session_for_issue.return_value = DevinSession(
        session_id="sess-001",
        url="https://app.devin.ai/sessions/sess-001",
        status="running",
    )
    mock.terminate_session.return_value = None
    mock.send_message.return_value = None
    return mock


# ── parse_slash_command tests ──


def test_parse_proceed() -> None:
    """/proceed recognized."""
    assert parse_slash_command("/proceed") == "/proceed"


def test_parse_sgtm() -> None:
    """/sgtm recognized (alias for proceed)."""
    assert parse_slash_command("/sgtm") == "/sgtm"


def test_parse_close() -> None:
    """/close recognized."""
    assert parse_slash_command("/close") == "/close"


def test_parse_skip() -> None:
    """/skip recognized."""
    assert parse_slash_command("/skip") == "/skip"


def test_parse_triage() -> None:
    """/triage recognized."""
    assert parse_slash_command("/triage") == "/triage"


def test_parse_retriage() -> None:
    """/retriage recognized."""
    assert parse_slash_command("/retriage") == "/retriage"


def test_parse_not_command() -> None:
    """Regular comment returns None."""
    assert parse_slash_command("This is a regular comment") is None


def test_parse_command_with_trailing_text() -> None:
    """/proceed looks good still recognized."""
    assert parse_slash_command("/proceed looks good") == "/proceed"


def test_parse_command_case_insensitive() -> None:
    """/Proceed works."""
    assert parse_slash_command("/Proceed") == "/proceed"


def test_parse_empty_body() -> None:
    """Empty body returns None."""
    assert parse_slash_command("") is None
    assert parse_slash_command("   ") is None


# ── execute command tests ──


@pytest.mark.asyncio
async def test_proceed_swaps_label(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """triaged -> implement label swap."""
    github.get_labels.return_value = ["bug", "devin:triaged"]
    await handle_comment(42, "emily-ross", "/proceed", github, devin, settings)
    github.swap_label.assert_called_once_with(42, "devin:triaged", "devin:implement")


@pytest.mark.asyncio
async def test_proceed_invalid_state(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """No-op if not in triaged state."""
    github.get_labels.return_value = ["bug", "devin:triage"]
    await handle_comment(42, "emily-ross", "/proceed", github, devin, settings)
    github.swap_label.assert_not_called()


@pytest.mark.asyncio
async def test_close_removes_labels_and_closes(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Removes all devin labels, closes issue."""
    await handle_comment(42, "emily-ross", "/close", github, devin, settings)
    github.remove_all_devin_labels.assert_called_once_with(42)
    github.close_issue.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_close_terminates_active_session(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Active session terminated on /close."""
    await handle_comment(42, "emily-ross", "/close", github, devin, settings)
    devin.terminate_session.assert_called_once_with("sess-001")


@pytest.mark.asyncio
async def test_skip_adds_label_and_terminates(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Adds skip label, terminates active session."""
    await handle_comment(42, "emily-ross", "/skip", github, devin, settings)
    github.remove_all_devin_labels.assert_called_once_with(42)
    github.add_label.assert_called_once_with(42, "devin:skip")
    devin.terminate_session.assert_called_once_with("sess-001")


@pytest.mark.asyncio
async def test_triage_on_unlabeled_issue(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Adds triage label on unlabeled issue."""
    github.get_labels.return_value = ["bug"]
    await handle_comment(42, "emily-ross", "/triage", github, devin, settings)
    github.add_label.assert_called_once_with(42, "devin:triage")


@pytest.mark.asyncio
async def test_triage_on_already_labeled(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """No-op if already has devin status label."""
    github.get_labels.return_value = ["bug", "devin:triaged"]
    await handle_comment(42, "emily-ross", "/triage", github, devin, settings)
    github.add_label.assert_not_called()


@pytest.mark.asyncio
async def test_retriage_resets_to_triage(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Removes current label, adds triage."""
    github.get_labels.return_value = ["bug", "devin:triaged"]
    await handle_comment(42, "emily-ross", "/retriage", github, devin, settings)
    github.remove_all_devin_labels.assert_called()
    github.add_label.assert_called_with(42, "devin:triage")


@pytest.mark.asyncio
async def test_non_command_forwards_to_session(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Forwards to active Devin session."""
    await handle_comment(42, "emily-ross", "Can you also check the tests?", github, devin, settings)
    devin.send_message.assert_called_once()
    call_args = devin.send_message.call_args
    assert "sess-001" in call_args[0]
    assert "Can you also check the tests?" in call_args[0][1]


@pytest.mark.asyncio
async def test_non_command_no_active_session(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """No-op if no active session."""
    devin.get_active_session_for_issue.return_value = None
    await handle_comment(42, "emily-ross", "Just a comment", github, devin, settings)
    devin.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_bot_comments_ignored(
    github: AsyncMock, devin: AsyncMock, settings: Settings
) -> None:
    """Comments from devin-ai-integration[bot] are ignored."""
    await handle_comment(42, "devin-ai-integration[bot]", "/proceed", github, devin, settings)
    github.swap_label.assert_not_called()
    devin.send_message.assert_not_called()
