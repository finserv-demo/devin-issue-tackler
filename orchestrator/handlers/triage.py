"""Triage pipeline handler.

When a new issue is opened (or devin:triage label is applied), add a eyes
reaction, create a Devin triage session with the appropriate playbook and
context, and tag it for reverse-lookup.
"""

import logging

from orchestrator.config import Settings
from orchestrator.context import build_triage_context
from orchestrator.devin_client import DevinClient
from orchestrator.github_client import GitHubClient
from orchestrator.labels import DevinControl

logger = logging.getLogger(__name__)


async def handle_triage(
    issue_number: int,
    github: GitHubClient,
    devin: DevinClient,
    settings: Settings,
) -> None:
    """Start a triage session for the given issue.

    1. Check issue doesn't have devin:skip label
    2. Add eyes reaction to the issue (visual confirmation)
    3. Build context prompt from issue data + comments
    4. Create Devin session with triage playbook, tags, and ACU limit

    Args:
        issue_number: The GitHub issue number.
        github: GitHubClient instance.
        devin: DevinClient instance.
        settings: Application settings.
    """
    # Check if opted out
    labels = await github.get_labels(issue_number)
    if DevinControl.SKIP in labels:
        logger.info("Issue #%d has %s label, skipping triage", issue_number, DevinControl.SKIP)
        return

    # Add eyes reaction
    reaction_id = await github.add_reaction(issue_number, "eyes")
    logger.info("Added eyes reaction (id=%d) to issue #%d", reaction_id, issue_number)

    # Build context
    context = await build_triage_context(issue_number, github)

    # Build tags for reverse-lookup
    tags = [
        "backlog-auto",
        f"issue:{issue_number}",
        "stage:triage",
        f"repo:{settings.target_repo}",
    ]

    # Create Devin session
    session = await devin.create_session(
        prompt=context,
        playbook_id=settings.triage_playbook_id or None,
        tags=tags,
        max_acu_limit=settings.acu_limit_triage,
    )

    logger.info(
        "Created triage session %s for issue #%d: %s",
        session.session_id,
        issue_number,
        session.url,
    )
