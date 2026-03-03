"""Implementation pipeline handler.

When devin:implement label is applied (after /proceed), add a eyes reaction,
assemble full context (issue + triage analysis + human comments), and create
a Devin implement session.
"""

import logging

from orchestrator.config import Settings
from orchestrator.context import build_implement_context
from orchestrator.devin_client import DevinClient
from orchestrator.github_client import GitHubClient

logger = logging.getLogger(__name__)


async def handle_implement(
    issue_number: int,
    github: GitHubClient,
    devin: DevinClient,
    settings: Settings,
) -> None:
    """Start an implementation session for the given issue.

    1. Add eyes reaction to the issue
    2. Build full context (issue + all comments including triage analysis)
    3. Create Devin session with implement playbook, tags, and ACU limit

    Args:
        issue_number: The GitHub issue number.
        github: GitHubClient instance.
        devin: DevinClient instance.
        settings: Application settings.
    """
    # Add eyes reaction
    reaction_id = await github.add_reaction(issue_number, "eyes")
    logger.info("Added eyes reaction (id=%d) to issue #%d", reaction_id, issue_number)

    # Build context
    context = await build_implement_context(issue_number, github)

    # Build tags for reverse-lookup
    tags = [
        "backlog-auto",
        f"issue:{issue_number}",
        "stage:implement",
        f"repo:{settings.target_repo}",
    ]

    # Create Devin session
    session = await devin.create_session(
        prompt=context,
        playbook_id=settings.implement_playbook_id or None,
        tags=tags,
        max_acu_limit=settings.acu_limit_implement,
    )

    logger.info(
        "Created implement session %s for issue #%d: %s",
        session.session_id,
        issue_number,
        session.url,
    )
