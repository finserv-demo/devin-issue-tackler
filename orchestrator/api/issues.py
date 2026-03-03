"""Dashboard API: Issue endpoints.

These endpoints serve the dashboard frontend with issue data.
In Phase 3 (this implementation), they return mock data that matches
the real schema. The actual database integration happens when
Phase 1/2 models.py + DB migrations are merged.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException

from orchestrator.labels import DevinSizing, DevinStatus
from orchestrator.schemas.api import (
    CommandRequest,
    CommandResponse,
    CommentRequest,
    IssueDetail,
    IssueSummary,
    SessionSummary,
    TimelineEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/issues", tags=["issues"])


def _time_ago(hours: float) -> str:
    """Format hours as a human-readable 'time ago' string."""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes}m ago"
    if hours < 24:
        return f"{int(hours)}h ago"
    days = int(hours / 24)
    return f"{days}d ago"


def _get_status_from_labels(labels: list[str]) -> str:
    """Extract pipeline status from labels."""
    status_map = {
        DevinStatus.TRIAGE.value: "triage",
        DevinStatus.TRIAGED.value: "triaged",
        DevinStatus.IMPLEMENT.value: "implement",
        DevinStatus.PR_OPENED.value: "pr-opened",
        DevinStatus.DONE.value: "done",
        DevinStatus.ESCALATED.value: "escalated",
    }
    for label in labels:
        if label in status_map:
            return status_map[label]
    return "new"


def _get_sizing_from_labels(labels: list[str]) -> str | None:
    """Extract sizing from labels."""
    sizing_map = {
        DevinSizing.GREEN.value: "green",
        DevinSizing.YELLOW.value: "yellow",
        DevinSizing.RED.value: "red",
    }
    for label in labels:
        if label in sizing_map:
            return sizing_map[label]
    return None


def _needs_attention(status: str) -> tuple[bool, str | None]:
    """Determine if an issue needs human attention."""
    if status == "escalated":
        return True, "Devin is stuck and needs human help"
    if status == "pr-opened":
        return True, "PR is ready for review"
    if status == "triaged":
        return True, "Ready to proceed with implementation"
    return False, None


def _get_available_actions(status: str) -> list[str]:
    """Get available actions based on current status."""
    if status == "triaged":
        return ["proceed", "close", "feedback"]
    if status == "pr-opened":
        return ["proceed", "close", "feedback"]
    if status == "escalated":
        return ["proceed", "close", "feedback"]
    if status in ("triage", "implement"):
        return ["close", "feedback"]
    if status == "new":
        return ["proceed", "close"]
    return ["close"]


def _get_next_steps(status: str) -> str:
    """Get description of next steps based on status."""
    steps: dict[str, str] = {
        "new": "This issue hasn't been triaged yet. Click Proceed to start triage.",
        "triage": "Devin is analyzing this issue to determine scope and approach.",
        "triaged": "Triage complete. Click Proceed to start implementation, or provide feedback on the plan.",
        "implement": "Devin is working on the implementation. You can provide feedback while it works.",
        "pr-opened": "A PR has been opened. Review the changes and click Proceed to approve, or provide feedback.",
        "done": "This issue has been resolved.",
        "escalated": "Devin needs help. Review the situation and provide feedback or click Proceed to retry.",
    }
    return steps.get(status, "")


# ── Mock data for Phase 3 dashboard development ──

_NOW = datetime.now(UTC)

_MOCK_ISSUES: list[dict[str, object]] = [
    {
        "number": 101,
        "title": "Fix portfolio calculation rounding errors",
        "body": "The portfolio service calculates returns with floating point errors that compound over time.\n\nSteps to reproduce:\n1. Create portfolio with multiple positions\n2. Calculate daily returns over 30 days\n3. Compare with manual calculation\n\nExpected: Values match within 0.01%\nActual: Drift of up to 0.5% after 30 days",
        "labels": ["devin:pr-opened", "devin:green", "bug"],
        "state": "open",
        "created_at": (_NOW - timedelta(days=3)).isoformat(),
        "updated_at": (_NOW - timedelta(hours=2)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/101",
        "hours_in_state": 2.0,
        "pr_url": "https://github.com/finserv-demo/finserv/pull/105",
        "pr_number": 105,
    },
    {
        "number": 102,
        "title": "Add risk assessment endpoint for new asset classes",
        "body": "The risk engine currently only supports equities and bonds. We need to add support for:\n- Commodities\n- Crypto assets\n- Real estate investment trusts (REITs)",
        "labels": ["devin:escalated", "devin:yellow", "enhancement"],
        "state": "open",
        "created_at": (_NOW - timedelta(days=5)).isoformat(),
        "updated_at": (_NOW - timedelta(hours=6)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/102",
        "hours_in_state": 6.0,
    },
    {
        "number": 103,
        "title": "Implement tax-loss harvesting suggestions",
        "body": "Add an endpoint that analyzes a portfolio and suggests tax-loss harvesting opportunities.",
        "labels": ["devin:implement", "devin:yellow", "enhancement"],
        "state": "open",
        "created_at": (_NOW - timedelta(days=2)).isoformat(),
        "updated_at": (_NOW - timedelta(hours=1)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/103",
        "hours_in_state": 1.0,
    },
    {
        "number": 104,
        "title": "Fix notification service email template rendering",
        "body": "Email notifications are rendering HTML tags as plain text instead of formatting them.",
        "labels": ["devin:triaged", "devin:green", "bug"],
        "state": "open",
        "created_at": (_NOW - timedelta(days=1)).isoformat(),
        "updated_at": (_NOW - timedelta(hours=4)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/104",
        "hours_in_state": 4.0,
    },
    {
        "number": 105,
        "title": "Add WebSocket support for real-time market data",
        "body": "Currently the market data service only supports polling. We need WebSocket streaming for real-time price updates.",
        "labels": ["devin:triaged", "devin:red", "enhancement"],
        "state": "open",
        "created_at": (_NOW - timedelta(days=7)).isoformat(),
        "updated_at": (_NOW - timedelta(days=1)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/105",
        "hours_in_state": 24.0,
    },
    {
        "number": 106,
        "title": "Onboarding flow skips KYC verification step",
        "body": "When a user completes the onboarding flow, the KYC verification step is sometimes skipped if they navigate back and forward.",
        "labels": ["devin:triage", "bug"],
        "state": "open",
        "created_at": (_NOW - timedelta(hours=12)).isoformat(),
        "updated_at": (_NOW - timedelta(hours=11)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/106",
        "hours_in_state": 11.0,
    },
    {
        "number": 107,
        "title": "Add portfolio rebalancing recommendations",
        "body": "Implement an endpoint that generates rebalancing recommendations based on target allocations.",
        "labels": ["devin:done", "devin:green", "enhancement"],
        "state": "closed",
        "created_at": (_NOW - timedelta(days=10)).isoformat(),
        "updated_at": (_NOW - timedelta(days=2)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/107",
        "hours_in_state": 48.0,
        "pr_url": "https://github.com/finserv-demo/finserv/pull/110",
        "pr_number": 110,
    },
    {
        "number": 108,
        "title": "Improve market data caching strategy",
        "body": "Market data API calls are not cached efficiently, leading to rate limit issues with the data provider.",
        "labels": ["devin:done", "devin:green", "performance"],
        "state": "closed",
        "created_at": (_NOW - timedelta(days=8)).isoformat(),
        "updated_at": (_NOW - timedelta(days=1)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/108",
        "hours_in_state": 24.0,
        "pr_url": "https://github.com/finserv-demo/finserv/pull/111",
        "pr_number": 111,
    },
    {
        "number": 109,
        "title": "Add batch processing for tax calculations",
        "body": "Tax calculations for large portfolios time out. Need batch processing support.",
        "labels": ["devin:implement", "devin:green", "performance"],
        "state": "open",
        "created_at": (_NOW - timedelta(days=4)).isoformat(),
        "updated_at": (_NOW - timedelta(hours=3)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/109",
        "hours_in_state": 3.0,
    },
    {
        "number": 110,
        "title": "Fix CORS headers for dashboard API",
        "body": "Dashboard can't reach the API from a different origin in production.",
        "labels": ["bug"],
        "state": "open",
        "created_at": (_NOW - timedelta(hours=6)).isoformat(),
        "updated_at": (_NOW - timedelta(hours=6)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/110",
        "hours_in_state": 6.0,
    },
    {
        "number": 111,
        "title": "Upgrade FastAPI to v0.115 across all services",
        "body": "All backend services are on FastAPI 0.104. Need to upgrade to 0.115 for latest security patches.",
        "labels": ["devin:pr-opened", "devin:green", "maintenance"],
        "state": "open",
        "created_at": (_NOW - timedelta(days=2)).isoformat(),
        "updated_at": (_NOW - timedelta(hours=5)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/111",
        "hours_in_state": 5.0,
        "pr_url": "https://github.com/finserv-demo/finserv/pull/115",
        "pr_number": 115,
    },
    {
        "number": 112,
        "title": "Add integration tests for onboarding flow",
        "body": "No integration tests cover the full onboarding flow end-to-end.",
        "labels": ["devin:done", "devin:yellow", "testing"],
        "state": "closed",
        "created_at": (_NOW - timedelta(days=12)).isoformat(),
        "updated_at": (_NOW - timedelta(days=3)).isoformat(),
        "html_url": "https://github.com/finserv-demo/finserv/issues/112",
        "hours_in_state": 72.0,
        "pr_url": "https://github.com/finserv-demo/finserv/pull/116",
        "pr_number": 116,
    },
]


def _build_issue_summary(issue: dict[str, object]) -> IssueSummary:
    labels = list(issue.get("labels", []))  # type: ignore[arg-type]
    status = _get_status_from_labels(labels)
    sizing = _get_sizing_from_labels(labels)
    needs_attn, reason = _needs_attention(status)
    hours = float(issue.get("hours_in_state", 0))

    return IssueSummary(
        number=int(issue["number"]),  # type: ignore[arg-type]
        title=str(issue["title"]),
        state=str(issue["state"]),
        status=status,
        sizing=sizing,
        labels=labels,
        created_at=str(issue.get("created_at", "")),
        updated_at=str(issue.get("updated_at", "")),
        time_in_state=_time_ago(hours),
        html_url=str(issue.get("html_url", "")),
        pr_url=str(issue["pr_url"]) if issue.get("pr_url") else None,
        needs_attention=needs_attn,
        attention_reason=reason,
    )


def _build_mock_timeline(issue: dict[str, object], status: str) -> list[TimelineEntry]:
    """Build a realistic mock timeline for an issue."""
    entries: list[TimelineEntry] = []
    created = str(issue.get("created_at", _NOW.isoformat()))

    entries.append(TimelineEntry(
        type="state_change",
        timestamp=created,
        actor="github-actions",
        body="Issue opened",
        to_state="new",
    ))

    if status in ("triage", "triaged", "implement", "pr-opened", "done", "escalated"):
        t = (datetime.fromisoformat(created) + timedelta(minutes=5)).isoformat()
        entries.append(TimelineEntry(
            type="label",
            timestamp=t,
            actor="finserv-backlog-bot",
            label="devin:triage",
            body="Started triage",
        ))
        entries.append(TimelineEntry(
            type="session_event",
            timestamp=(datetime.fromisoformat(created) + timedelta(minutes=6)).isoformat(),
            actor="Devin",
            body="Triage session started. Analyzing issue scope and affected services.",
            session_url="https://app.devin.ai/sessions/mock-triage-session",
        ))

    if status in ("triaged", "implement", "pr-opened", "done", "escalated"):
        t = (datetime.fromisoformat(created) + timedelta(hours=1)).isoformat()
        entries.append(TimelineEntry(
            type="comment",
            timestamp=t,
            actor="devin-ai-integration[bot]",
            body="**Triage Complete**\n\nThis issue affects the portfolio service. Estimated effort: small (< 2 hours).\n\n**Recommended approach:** Fix the floating point precision by using `Decimal` types for all monetary calculations.",
        ))
        entries.append(TimelineEntry(
            type="state_change",
            timestamp=t,
            actor="finserv-backlog-bot",
            from_state="triage",
            to_state="triaged",
            body="Triage completed",
        ))

    if status in ("implement", "pr-opened", "done"):
        t = (datetime.fromisoformat(created) + timedelta(hours=2)).isoformat()
        entries.append(TimelineEntry(
            type="state_change",
            timestamp=t,
            actor="finserv-backlog-bot",
            from_state="triaged",
            to_state="implement",
            body="Implementation started",
        ))
        entries.append(TimelineEntry(
            type="session_event",
            timestamp=(datetime.fromisoformat(created) + timedelta(hours=2, minutes=1)).isoformat(),
            actor="Devin",
            body="Implementation session started. Working on the fix.",
            session_url="https://app.devin.ai/sessions/mock-implement-session",
        ))

    if status in ("pr-opened", "done"):
        t = (datetime.fromisoformat(created) + timedelta(hours=4)).isoformat()
        entries.append(TimelineEntry(
            type="state_change",
            timestamp=t,
            actor="finserv-backlog-bot",
            from_state="implement",
            to_state="pr-opened",
            body="Pull request opened",
        ))
        entries.append(TimelineEntry(
            type="comment",
            timestamp=t,
            actor="devin-ai-integration[bot]",
            body="PR opened: [#105](https://github.com/finserv-demo/finserv/pull/105)\n\nChanges:\n- Converted monetary fields to Decimal type\n- Added rounding to 2 decimal places at output boundaries\n- Updated tests to verify precision",
        ))

    if status == "escalated":
        t = str(issue.get("updated_at", _NOW.isoformat()))
        entries.append(TimelineEntry(
            type="state_change",
            timestamp=t,
            actor="finserv-backlog-bot",
            from_state="implement",
            to_state="escalated",
            body="Devin encountered issues and needs human help",
        ))
        entries.append(TimelineEntry(
            type="comment",
            timestamp=t,
            actor="devin-ai-integration[bot]",
            body="**Escalated**: I'm having trouble with the risk model calculations. The new asset classes require a different volatility model that I'm not confident about implementing without guidance.\n\n**What I tried:**\n- Extending the existing GARCH model\n- Adding separate volatility estimators\n\n**What I need:**\n- Guidance on which volatility model to use for crypto assets\n- Clarification on REIT risk weighting",
        ))

    if status == "done":
        t = str(issue.get("updated_at", _NOW.isoformat()))
        entries.append(TimelineEntry(
            type="state_change",
            timestamp=t,
            actor="finserv-backlog-bot",
            from_state="pr-opened",
            to_state="done",
            body="Issue resolved",
        ))

    return entries


@router.get("")
async def list_issues() -> list[IssueSummary]:
    """List all tracked issues with their current state."""
    return [_build_issue_summary(issue) for issue in _MOCK_ISSUES]


@router.get("/{number}")
async def get_issue(number: int) -> IssueDetail:
    """Get full issue detail including timeline."""
    for issue in _MOCK_ISSUES:
        if int(issue["number"]) == number:  # type: ignore[arg-type]
            labels = list(issue.get("labels", []))  # type: ignore[arg-type]
            status = _get_status_from_labels(labels)
            sizing = _get_sizing_from_labels(labels)
            needs_attn, reason = _needs_attention(status)
            actions = _get_available_actions(status)
            next_steps = _get_next_steps(status)
            timeline = _build_mock_timeline(issue, status)

            sessions: list[SessionSummary] = []
            if status not in ("new",):
                sessions.append(SessionSummary(
                    session_id="mock-triage-session",
                    stage="triage",
                    status="completed",
                    session_url="https://app.devin.ai/sessions/mock-triage-session",
                    acus_consumed=3.2,
                    created_at=str(issue.get("created_at", "")),
                ))
            if status in ("implement", "pr-opened", "done", "escalated"):
                impl_status = "completed" if status in ("pr-opened", "done") else "active"
                if status == "escalated":
                    impl_status = "failed"
                sessions.append(SessionSummary(
                    session_id="mock-implement-session",
                    stage="implement",
                    status=impl_status,
                    session_url="https://app.devin.ai/sessions/mock-implement-session",
                    acus_consumed=18.5,
                    created_at=str(issue.get("created_at", "")),
                ))

            return IssueDetail(
                number=int(issue["number"]),  # type: ignore[arg-type]
                title=str(issue["title"]),
                body=str(issue.get("body", "")),
                state=str(issue["state"]),
                status=status,
                sizing=sizing,
                labels=labels,
                created_at=str(issue.get("created_at", "")),
                updated_at=str(issue.get("updated_at", "")),
                html_url=str(issue.get("html_url", "")),
                pr_url=str(issue["pr_url"]) if issue.get("pr_url") else None,
                pr_number=int(issue["pr_number"]) if issue.get("pr_number") else None,
                needs_attention=needs_attn,
                attention_reason=reason,
                next_steps=next_steps,
                timeline=timeline,
                sessions=sessions,
                available_actions=actions,
            )

    raise HTTPException(status_code=404, detail=f"Issue #{number} not found")


@router.post("/{number}/comment")
async def post_comment(number: int, request: CommentRequest) -> CommandResponse:
    """Post a comment on an issue (→ GitHub + active Devin session)."""
    # In production, this would:
    # 1. Post comment to GitHub via github_client
    # 2. Forward to active Devin session via devin_client
    logger.info("Comment on issue #%d: %s", number, request.body[:100])
    return CommandResponse(success=True, message=f"Comment posted on issue #{number}")


@router.post("/{number}/command")
async def execute_command(number: int, request: CommandRequest) -> CommandResponse:
    """Execute a command on an issue (proceed, close, feedback)."""
    valid_actions = ("proceed", "close", "feedback")
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{request.action}'. Valid actions: {', '.join(valid_actions)}",
        )

    # In production, this would execute the corresponding slash command
    action_messages = {
        "proceed": f"Proceeding with issue #{number}",
        "close": f"Closing issue #{number}",
        "feedback": f"Feedback sent on issue #{number}",
    }

    logger.info("Command on issue #%d: %s (message: %s)", number, request.action, request.message[:100] if request.message else "")
    return CommandResponse(
        success=True,
        message=action_messages.get(request.action, f"Command '{request.action}' executed on issue #{number}"),
    )


@router.post("/triage-all")
async def triage_all() -> CommandResponse:
    """Bulk triage all open issues that haven't been triaged yet."""
    # Count "new" issues
    new_count = sum(
        1 for issue in _MOCK_ISSUES
        if _get_status_from_labels(list(issue.get("labels", []))) == "new"  # type: ignore[arg-type]
    )
    logger.info("Bulk triage requested for %d new issues", new_count)
    return CommandResponse(
        success=True,
        message=f"Triage started for {new_count} new issue(s)",
    )
