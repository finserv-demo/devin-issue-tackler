"""Context builders for Devin sessions.

Assembles prompt context from GitHub issue data and comments for triage
and implementation sessions.
"""

import logging

from orchestrator.github_client import GitHubClient

logger = logging.getLogger(__name__)


async def build_triage_context(issue_number: int, github: GitHubClient) -> str:
    """Assemble the prompt context for a triage session.

    Fetches issue details and all comments from the GitHub API.
    Returns formatted markdown prompt.

    Args:
        issue_number: The GitHub issue number.
        github: GitHubClient instance.

    Returns:
        Formatted markdown string with issue context.
    """
    issue = await github.get_issue(issue_number)
    comments = await github.get_issue_comments(issue_number)

    lines = [
        f"# Triage Issue #{issue_number}: {issue.title}",
        "",
        f"**URL:** {issue.html_url}",
        f"**State:** {issue.state}",
        f"**Labels:** {', '.join(issue.labels) if issue.labels else 'none'}",
        "",
        "## Issue Body",
        "",
        issue.body or "_No description provided._",
        "",
    ]

    if comments:
        lines.append("## Comments")
        lines.append("")
        for comment in comments:
            lines.append(f"### @{comment.author} ({comment.created_at})")
            lines.append("")
            lines.append(comment.body)
            lines.append("")

    return "\n".join(lines)


async def build_implement_context(issue_number: int, github: GitHubClient) -> str:
    """Assemble the prompt context for an implement session.

    Includes issue details, all comments (including triage analysis and human
    feedback), for a complete picture.

    Args:
        issue_number: The GitHub issue number.
        github: GitHubClient instance.

    Returns:
        Formatted markdown string with full context for implementation.
    """
    issue = await github.get_issue(issue_number)
    comments = await github.get_issue_comments(issue_number)

    lines = [
        f"# Implement Issue #{issue_number}: {issue.title}",
        "",
        f"**URL:** {issue.html_url}",
        f"**State:** {issue.state}",
        f"**Labels:** {', '.join(issue.labels) if issue.labels else 'none'}",
        "",
        "## Issue Body",
        "",
        issue.body or "_No description provided._",
        "",
    ]

    if comments:
        lines.append("## Comments & Triage Analysis")
        lines.append("")
        for comment in comments:
            lines.append(f"### @{comment.author} ({comment.created_at})")
            lines.append("")
            lines.append(comment.body)
            lines.append("")

    lines.append("## Instructions")
    lines.append("")
    lines.append("Implement the changes described in the issue and triage analysis above.")
    lines.append("Follow the implementation plan from the triage comment.")
    lines.append("")

    return "\n".join(lines)
