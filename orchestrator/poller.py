"""Session poller and status sync.

Background task that monitors active Devin sessions, detects completion/failure,
syncs status back to GitHub, and mirrors Devin UI messages to GitHub comments.
"""

import asyncio
import logging

from orchestrator.config import Settings
from orchestrator.devin_client import DevinClient
from orchestrator.github_client import GitHubClient

logger = logging.getLogger(__name__)

_COMPLETED_STATUSES = {"exit", "error"}
_ACTIVE_STATUSES = {"new", "claimed", "running", "resuming"}


class SessionPoller:
    """Background task that runs every N seconds to sync Devin session state."""

    def __init__(self, github: GitHubClient, devin: DevinClient, settings: Settings) -> None:
        """Initialize the poller.

        Args:
            github: GitHubClient instance.
            devin: DevinClient instance.
            settings: Application settings.
        """
        self.github = github
        self.devin = devin
        self.settings = settings
        self._active_sessions: dict[str, int] = {}  # session_id -> issue_number
        self._message_cursors: dict[str, str] = {}  # session_id -> last cursor
        self._eyes_reactions: dict[str, tuple[int, int]] = {}  # session_id -> (issue_number, reaction_id)

    def register_session(
        self,
        session_id: str,
        issue_number: int,
        reaction_id: int | None = None,
    ) -> None:
        """Register a new session for polling.

        Called by triage/implement handlers after creating a session.

        Args:
            session_id: The Devin session ID.
            issue_number: The GitHub issue number.
            reaction_id: The eyes reaction ID to remove on completion.
        """
        self._active_sessions[session_id] = issue_number
        if reaction_id is not None:
            self._eyes_reactions[session_id] = (issue_number, reaction_id)
        logger.info("Registered session %s for issue #%d (reaction_id=%s)", session_id, issue_number, reaction_id)

    async def poll_once(self) -> None:
        """Single poll cycle -- check all active sessions."""
        if not self._active_sessions:
            return

        # Copy keys to avoid mutation during iteration
        session_ids = list(self._active_sessions.keys())

        for session_id in session_ids:
            issue_number = self._active_sessions.get(session_id)
            if issue_number is None:
                continue

            try:
                session = await self.devin.get_session(session_id)

                # Check if session completed
                if session.status in _COMPLETED_STATUSES:
                    await self._handle_session_complete(session_id, session.status, issue_number)
                    continue

                # Mirror Devin UI messages to GitHub
                await self._mirror_messages(session_id, issue_number)

            except Exception:
                logger.exception("Error polling session %s for issue #%d", session_id, issue_number)

    async def _handle_session_complete(
        self,
        session_id: str,
        status: str,
        issue_number: int,
    ) -> None:
        """Session finished -- remove eyes reaction, clean up tracking.

        Args:
            session_id: The Devin session ID.
            status: The session's final status.
            issue_number: The GitHub issue number.
        """
        logger.info("Session %s completed with status %r for issue #%d", session_id, status, issue_number)

        # Remove eyes reaction if still present
        if session_id in self._eyes_reactions:
            reaction_issue, reaction_id = self._eyes_reactions[session_id]
            try:
                await self.github.remove_reaction(reaction_issue, reaction_id)
                logger.info("Removed eyes reaction from issue #%d", reaction_issue)
            except Exception:
                logger.exception("Failed to remove eyes reaction from issue #%d", reaction_issue)
            del self._eyes_reactions[session_id]

        # Clean up tracking
        self._active_sessions.pop(session_id, None)
        self._message_cursors.pop(session_id, None)

    async def _mirror_messages(self, session_id: str, issue_number: int) -> None:
        """Poll for new messages from Devin UI and mirror user messages to GitHub.

        Only mirrors messages with source="user" (sent by humans via Devin UI).
        Devin's own messages are not mirrored since Devin posts directly to GitHub.

        Args:
            session_id: The Devin session ID.
            issue_number: The GitHub issue number.
        """
        cursor = self._message_cursors.get(session_id)
        page = await self.devin.list_messages(session_id, after=cursor)

        for msg in page.items:
            if msg.source == "user":
                try:
                    await self.github.post_comment(
                        issue_number,
                        f"> **via Devin UI** (source: {msg.source}):\n> {msg.message}",
                    )
                except Exception:
                    logger.exception("Failed to mirror message to issue #%d", issue_number)

        if page.items and page.end_cursor:
            self._message_cursors[session_id] = page.end_cursor

    async def recover_sessions(self) -> None:
        """Recover active sessions on startup by querying Devin API.

        Discovers all active sessions tagged with 'backlog-auto' and re-registers
        them for polling.
        """
        try:
            sessions = await self.devin.list_sessions_by_tags(["backlog-auto"])
            for session in sessions:
                if session.status in _ACTIVE_STATUSES:
                    # Extract issue number from tags
                    issue_number = self._extract_issue_number(session.tags)
                    if issue_number:
                        self._active_sessions[session.session_id] = issue_number
                        logger.info(
                            "Recovered session %s for issue #%d (status=%s)",
                            session.session_id,
                            issue_number,
                            session.status,
                        )
            logger.info("Recovered %d active sessions", len(self._active_sessions))
        except Exception:
            logger.exception("Failed to recover sessions on startup")

    @staticmethod
    def _extract_issue_number(tags: list[str]) -> int | None:
        """Extract issue number from session tags.

        Looks for a tag matching the pattern 'issue:{number}'.

        Args:
            tags: List of session tags.

        Returns:
            The issue number, or None if not found.
        """
        for tag in tags:
            if tag.startswith("issue:"):
                try:
                    return int(tag[len("issue:"):])
                except ValueError:
                    continue
        return None

    async def run_forever(self) -> None:
        """Main loop -- called as a background task on app startup."""
        logger.info("Session poller started (interval=%ds)", self.settings.polling_interval_seconds)
        await self.recover_sessions()
        while True:
            try:
                await self.poll_once()
            except Exception:
                logger.exception("Error in poller cycle")
            await asyncio.sleep(self.settings.polling_interval_seconds)
