"""Tests for the session poller and status sync."""

from unittest.mock import AsyncMock

import pytest

from orchestrator.config import Settings
from orchestrator.poller import SessionPoller
from orchestrator.schemas.devin import DevinSession, Message, MessagePage


@pytest.fixture
def settings() -> Settings:
    return Settings(
        github_token="ghp_test",
        devin_api_key="cog_test",
        devin_org_id="org-test",
        polling_interval_seconds=5,
    )


@pytest.fixture
def github() -> AsyncMock:
    mock = AsyncMock()
    mock.remove_reaction.return_value = None
    mock.post_comment.return_value = None
    return mock


@pytest.fixture
def devin() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def poller(github: AsyncMock, devin: AsyncMock, settings: Settings) -> SessionPoller:
    return SessionPoller(github=github, devin=devin, settings=settings)


@pytest.mark.asyncio
async def test_poll_detects_completed_session(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """Session with status 'exit' triggers cleanup."""
    poller.register_session("sess-001", 42, reaction_id=999)
    devin.get_session.return_value = DevinSession(session_id="sess-001", status="exit")
    devin.list_messages.return_value = MessagePage(items=[])

    await poller.poll_once()

    assert "sess-001" not in poller._active_sessions
    github.remove_reaction.assert_called_once_with(42, 999)


@pytest.mark.asyncio
async def test_poll_detects_errored_session(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """Session with status 'error' triggers cleanup."""
    poller.register_session("sess-001", 42, reaction_id=888)
    devin.get_session.return_value = DevinSession(session_id="sess-001", status="error")
    devin.list_messages.return_value = MessagePage(items=[])

    await poller.poll_once()

    assert "sess-001" not in poller._active_sessions
    github.remove_reaction.assert_called_once_with(42, 888)


@pytest.mark.asyncio
async def test_poll_ignores_running_session(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """Running sessions are not cleaned up."""
    poller.register_session("sess-001", 42, reaction_id=999)
    devin.get_session.return_value = DevinSession(session_id="sess-001", status="running")
    devin.list_messages.return_value = MessagePage(items=[])

    await poller.poll_once()

    assert "sess-001" in poller._active_sessions
    github.remove_reaction.assert_not_called()


@pytest.mark.asyncio
async def test_poll_removes_eyes_reaction(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """Eyes reaction removed when session completes."""
    poller.register_session("sess-001", 42, reaction_id=777)
    devin.get_session.return_value = DevinSession(session_id="sess-001", status="exit")
    devin.list_messages.return_value = MessagePage(items=[])

    await poller.poll_once()

    github.remove_reaction.assert_called_once_with(42, 777)
    assert "sess-001" not in poller._eyes_reactions


@pytest.mark.asyncio
async def test_poll_mirrors_user_messages(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """User messages from Devin UI posted to GitHub."""
    poller.register_session("sess-001", 42)
    devin.get_session.return_value = DevinSession(session_id="sess-001", status="running")
    devin.list_messages.return_value = MessagePage(
        items=[
            Message(event_id="evt-001", source="user", message="Please check auth service", created_at=1700000000),
        ],
        has_next_page=False,
        end_cursor="cursor-1",
    )

    await poller.poll_once()

    github.post_comment.assert_called_once()
    call_args = github.post_comment.call_args
    assert call_args[0][0] == 42
    assert "Please check auth service" in call_args[0][1]
    assert "@user" not in call_args[0][1]  # no accidental GitHub mention


@pytest.mark.asyncio
async def test_poll_skips_devin_messages(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """Devin-source messages not mirrored."""
    poller.register_session("sess-001", 42)
    devin.get_session.return_value = DevinSession(session_id="sess-001", status="running")
    devin.list_messages.return_value = MessagePage(
        items=[
            Message(event_id="evt-001", source="devin", message="Working on it...", created_at=1700000000),
        ],
        has_next_page=False,
        end_cursor="cursor-1",
    )

    await poller.poll_once()

    github.post_comment.assert_not_called()


@pytest.mark.asyncio
async def test_poll_updates_cursor(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """Cursor advanced after reading messages."""
    poller.register_session("sess-001", 42)
    devin.get_session.return_value = DevinSession(session_id="sess-001", status="running")
    devin.list_messages.return_value = MessagePage(
        items=[
            Message(event_id="evt-001", source="user", message="test msg", created_at=1700000000),
        ],
        has_next_page=False,
        end_cursor="cursor-abc",
    )

    await poller.poll_once()

    assert poller._message_cursors["sess-001"] == "cursor-abc"


@pytest.mark.asyncio
async def test_poll_empty_messages(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """No error when no new messages."""
    poller.register_session("sess-001", 42)
    devin.get_session.return_value = DevinSession(session_id="sess-001", status="running")
    devin.list_messages.return_value = MessagePage(items=[], has_next_page=False)

    await poller.poll_once()

    github.post_comment.assert_not_called()
    assert "sess-001" not in poller._message_cursors


@pytest.mark.asyncio
async def test_register_session(poller: SessionPoller) -> None:
    """Session added to active tracking."""
    poller.register_session("sess-001", 42, reaction_id=999)
    assert "sess-001" in poller._active_sessions
    assert poller._active_sessions["sess-001"] == 42
    assert poller._eyes_reactions["sess-001"] == (42, 999)


@pytest.mark.asyncio
async def test_session_removed_after_completion(
    poller: SessionPoller, devin: AsyncMock, github: AsyncMock
) -> None:
    """Completed sessions no longer polled."""
    poller.register_session("sess-001", 42)
    poller.register_session("sess-002", 43)

    # First session completes
    devin.get_session.side_effect = [
        DevinSession(session_id="sess-001", status="exit"),
        DevinSession(session_id="sess-002", status="running"),
    ]
    devin.list_messages.return_value = MessagePage(items=[])

    await poller.poll_once()

    assert "sess-001" not in poller._active_sessions
    assert "sess-002" in poller._active_sessions
