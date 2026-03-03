"""Slash command handler for issue comments.

Parses comments for slash commands (/proceed, /sgtm, /close, /skip, /triage,
/retriage) and executes the corresponding label transitions. Non-command
comments are forwarded to active Devin sessions.
"""

import logging

from orchestrator.config import Settings
from orchestrator.devin_client import DevinClient
from orchestrator.github_client import GitHubClient
from orchestrator.labels import DevinControl, DevinStatus, get_current_status

logger = logging.getLogger(__name__)

SLASH_COMMANDS = {"/proceed", "/sgtm", "/close", "/skip", "/triage", "/retriage"}

# Bot authors to ignore (prevent loops)
BOT_AUTHORS = {"devin-ai-integration[bot]", "github-actions[bot]"}


def parse_slash_command(body: str) -> str | None:
    """Extract slash command from comment body.

    Must be the first word of the comment. Case-insensitive.

    Args:
        body: The comment body text.

    Returns:
        The slash command (lowercase) if found, or None.
    """
    if not body or not body.strip():
        return None
    first_word = body.strip().split()[0].lower()
    return first_word if first_word in SLASH_COMMANDS else None


async def handle_comment(
    issue_number: int,
    author: str,
    body: str,
    github: GitHubClient,
    devin: DevinClient,
    settings: Settings,
) -> None:
    """Parse comment for slash commands. If found, execute.

    If not a slash command and there's an active session, forward the comment.
    Bot comments are ignored to prevent loops.

    Args:
        issue_number: The GitHub issue number.
        author: The comment author's login.
        body: The comment body text.
        github: GitHubClient instance.
        devin: DevinClient instance.
        settings: Application settings.
    """
    # Ignore bot comments to prevent loops
    if author in BOT_AUTHORS:
        logger.debug("Ignoring comment from bot author %s on issue #%d", author, issue_number)
        return

    command = parse_slash_command(body)
    if command:
        await execute_command(command, issue_number, github, devin, settings)
    else:
        await forward_comment_to_session(issue_number, author, body, devin)


async def execute_command(
    command: str,
    issue_number: int,
    github: GitHubClient,
    devin: DevinClient,
    settings: Settings,
) -> None:
    """Execute a slash command.

    Args:
        command: The slash command (e.g., "/proceed").
        issue_number: The GitHub issue number.
        github: GitHubClient instance.
        devin: DevinClient instance.
        settings: Application settings.
    """
    logger.info("Executing command %r on issue #%d", command, issue_number)

    labels = await github.get_labels(issue_number)
    current_status = get_current_status(labels)

    if command in ("/proceed", "/sgtm"):
        await _handle_proceed(issue_number, current_status, github)
    elif command == "/close":
        await _handle_close(issue_number, github, devin)
    elif command == "/skip":
        await _handle_skip(issue_number, github, devin)
    elif command == "/triage":
        await _handle_triage(issue_number, current_status, labels, github, settings)
    elif command == "/retriage":
        await _handle_retriage(issue_number, current_status, github, devin, settings)


async def _handle_proceed(
    issue_number: int,
    current_status: DevinStatus | None,
    github: GitHubClient,
) -> None:
    """Advance from triaged to implement."""
    if current_status != DevinStatus.TRIAGED:
        logger.warning(
            "Cannot /proceed on issue #%d: current status is %s (expected devin:triaged)",
            issue_number,
            current_status,
        )
        return

    await github.swap_label(issue_number, DevinStatus.TRIAGED, DevinStatus.IMPLEMENT)
    logger.info("Issue #%d: triaged -> implement", issue_number)


async def _handle_close(
    issue_number: int,
    github: GitHubClient,
    devin: DevinClient,
) -> None:
    """Remove all devin labels and close the issue."""
    # Terminate active session if any
    active_session = await devin.get_active_session_for_issue(issue_number)
    if active_session:
        try:
            await devin.terminate_session(active_session.session_id)
            logger.info("Terminated session %s for issue #%d", active_session.session_id, issue_number)
        except Exception:
            logger.exception("Failed to terminate session for issue #%d", issue_number)

    await github.remove_all_devin_labels(issue_number)
    await github.close_issue(issue_number)
    logger.info("Issue #%d closed via /close", issue_number)


async def _handle_skip(
    issue_number: int,
    github: GitHubClient,
    devin: DevinClient,
) -> None:
    """Add devin:skip label and terminate active session."""
    # Terminate active session if any
    active_session = await devin.get_active_session_for_issue(issue_number)
    if active_session:
        try:
            await devin.terminate_session(active_session.session_id)
            logger.info("Terminated session %s for issue #%d", active_session.session_id, issue_number)
        except Exception:
            logger.exception("Failed to terminate session for issue #%d", issue_number)

    await github.remove_all_devin_labels(issue_number)
    await github.add_label(issue_number, DevinControl.SKIP)
    logger.info("Issue #%d skipped via /skip", issue_number)


async def _handle_triage(
    issue_number: int,
    current_status: DevinStatus | None,
    labels: list[str],
    github: GitHubClient,
    settings: Settings,
) -> None:
    """Manually trigger triage on an issue with no devin status label."""
    if current_status is not None:
        logger.warning(
            "Cannot /triage on issue #%d: already has status %s",
            issue_number,
            current_status,
        )
        return

    if settings.opt_out_label in labels:
        logger.warning("Cannot /triage on issue #%d: has %s label", issue_number, settings.opt_out_label)
        return

    await github.add_label(issue_number, DevinStatus.TRIAGE)
    logger.info("Issue #%d: manual triage triggered", issue_number)


async def _handle_retriage(
    issue_number: int,
    current_status: DevinStatus | None,
    github: GitHubClient,
    devin: DevinClient,
    settings: Settings,
) -> None:
    """Terminate active session, remove current label and re-trigger triage."""
    labels = await github.get_labels(issue_number)
    if settings.opt_out_label in labels:
        logger.warning("Cannot /retriage on issue #%d: has %s label", issue_number, settings.opt_out_label)
        return

    # Terminate active session if any
    active_session = await devin.get_active_session_for_issue(issue_number)
    if active_session:
        try:
            await devin.terminate_session(active_session.session_id)
            logger.info("Terminated session %s for issue #%d", active_session.session_id, issue_number)
        except Exception:
            logger.exception("Failed to terminate session for issue #%d", issue_number)

    await github.remove_all_devin_labels(issue_number)
    await github.add_label(issue_number, DevinStatus.TRIAGE)
    logger.info("Issue #%d: retriage triggered", issue_number)


async def forward_comment_to_session(
    issue_number: int,
    author: str,
    body: str,
    devin: DevinClient,
) -> None:
    """Forward a non-command GitHub comment to the active Devin session.

    Args:
        issue_number: The GitHub issue number.
        author: The comment author's login.
        body: The comment body text.
        devin: DevinClient instance.
    """
    session = await devin.get_active_session_for_issue(issue_number)
    if session:
        await devin.send_message(
            session.session_id,
            f"New comment from @{author} on GitHub issue #{issue_number}:\n\n{body}",
        )
        logger.info("Forwarded comment from @%s to session %s", author, session.session_id)
    else:
        logger.debug("No active session for issue #%d, not forwarding comment", issue_number)
