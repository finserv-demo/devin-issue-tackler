"""Dashboard API endpoints.

Provides hero metrics and issue lists by querying the GitHub API
and Devin API. All data is fetched live — no local database.
"""

import asyncio
import logging
import math
from datetime import UTC, datetime, timedelta

import httpx

from orchestrator.config import Settings
from orchestrator.schemas.dashboard import (
    DashboardLists,
    DashboardMetrics,
    IssueItem,
    MetricCard,
)

logger = logging.getLogger(__name__)

# GitHub API helpers

_GITHUB_API = "https://api.github.com"


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _fetch_issues_by_label(
    client: httpx.AsyncClient,
    repo: str,
    token: str,
    label: str,
    state: str = "open",
) -> list[dict]:
    """Fetch all issues with a given label from GitHub."""
    all_issues: list[dict] = []
    page = 1
    while True:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{repo}/issues",
            headers=_github_headers(token),
            params={"labels": label, "state": state, "per_page": 100, "page": page},
            timeout=30.0,
        )
        resp.raise_for_status()
        items = resp.json()
        if not items:
            break
        for item in items:
            if "pull_request" not in item:
                all_issues.append(item)
        if len(items) < 100:
            break
        page += 1
    return all_issues


async def _fetch_issues_by_labels(
    client: httpx.AsyncClient,
    repo: str,
    token: str,
    labels: list[str],
    state: str = "open",
) -> list[dict]:
    """Fetch issues for multiple labels (union), concurrently."""
    per_label_results = await asyncio.gather(
        *[_fetch_issues_by_label(client, repo, token, label, state) for label in labels]
    )
    seen: set[int] = set()
    results: list[dict] = []
    for issues in per_label_results:
        for issue in issues:
            if issue["number"] not in seen:
                seen.add(issue["number"])
                results.append(issue)
    return results


def _time_ago(iso_str: str) -> str:
    """Convert ISO datetime string to a human-readable 'X ago' string."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(UTC) - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = delta.seconds // 60
        return f"{minutes}m ago"
    except (ValueError, AttributeError):
        return ""


def _extract_sizing(labels: list[dict]) -> str | None:
    """Extract the devin sizing label from a list of GitHub label objects."""
    for label in labels:
        name = label.get("name", "")
        if name in ("devin:green", "devin:yellow", "devin:red"):
            return name
    return None


def _extract_status(labels: list[dict]) -> str:
    """Extract the current devin status label."""
    for label in labels:
        name = label.get("name", "")
        if name.startswith("devin:") and name in (
            "devin:triage",
            "devin:triaged",
            "devin:implement",
            "devin:pr-opened",
            "devin:done",
            "devin:escalated",
        ):
            return name
    return ""


def _find_label_added_time(events: list[dict], target_label: str) -> str | None:
    """Find when a label was most recently added from timeline events."""
    latest: str | None = None
    for event in events:
        if event.get("event") == "labeled":
            label_obj = event.get("label", {})
            if label_obj.get("name") == target_label:
                latest = event.get("created_at", "")
    return latest


def _format_duration(delta: timedelta) -> str:
    """Format a timedelta as a human-readable string like '2.3d' or '4.1h'."""
    total_hours = delta.total_seconds() / 3600
    if total_hours >= 24:
        days = total_hours / 24
        return f"{days:.1f}d"
    return f"{total_hours:.1f}h"


def _issue_to_item(issue: dict) -> IssueItem:
    """Convert a GitHub issue dict to an IssueItem."""
    labels = issue.get("labels", [])
    status_label = _extract_status(labels)

    # Compute time_in_state from issue updated_at as a fallback
    updated = issue.get("updated_at", "")
    time_in_state = _time_ago(updated) if updated else ""

    return IssueItem(
        number=issue["number"],
        title=issue["title"],
        html_url=issue.get("html_url", ""),
        status_label=status_label,
        sizing_label=_extract_sizing(labels),
        time_in_state=time_in_state,
        pr_url=None,
        created_at=issue.get("created_at", ""),
    )


# ── Metrics computation ──


async def compute_metrics(settings: Settings, time_window_days: int = 7) -> DashboardMetrics:
    """Compute hero metrics for the dashboard.

    Fetches closed issues with devin:done label and computes:
    1. Issues resolved in current period + w/w change
    2. Median time to resolution + w/w change
    3. % resolved within 1 week of triage
    """
    repo = settings.target_repo
    token = settings.github_token

    now = datetime.now(UTC)
    current_start = now - timedelta(days=time_window_days)
    previous_start = current_start - timedelta(days=time_window_days)

    async with httpx.AsyncClient() as client:
        # Fetch all closed issues with devin:done
        done_issues = await _fetch_issues_by_label(client, repo, token, "devin:done", state="closed")

    # Split into current and previous periods
    current_resolved: list[dict] = []
    previous_resolved: list[dict] = []
    for issue in done_issues:
        closed_str = issue.get("closed_at", "")
        if not closed_str:
            continue
        try:
            closed_at = datetime.fromisoformat(closed_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if closed_at >= current_start:
            current_resolved.append(issue)
        elif closed_at >= previous_start:
            previous_resolved.append(issue)

    # 1. Issues resolved count
    current_count = len(current_resolved)
    previous_count = len(previous_resolved)
    if previous_count > 0:
        pct_change = ((current_count - previous_count) / previous_count) * 100
        wow_label = "w/w" if time_window_days == 7 else "m/m"
        sign = "+" if pct_change >= 0 else ""
        resolved_subtitle = f"{sign}{pct_change:.0f}% {wow_label}"
        # More resolved = good
        resolved_sentiment = "positive" if pct_change >= 0 else "negative"
    else:
        resolved_subtitle = ""
        resolved_sentiment = "neutral"

    period_label = "this week" if time_window_days == 7 else "this month"

    # 2. Median time to resolution
    def _resolution_time(issue: dict) -> timedelta | None:
        created = issue.get("created_at", "")
        closed = issue.get("closed_at", "")
        if not created or not closed:
            return None
        try:
            c = datetime.fromisoformat(created.replace("Z", "+00:00"))
            d = datetime.fromisoformat(closed.replace("Z", "+00:00"))
            return d - c
        except ValueError:
            return None

    current_times = [t for issue in current_resolved if (t := _resolution_time(issue)) is not None]
    previous_times = [t for issue in previous_resolved if (t := _resolution_time(issue)) is not None]

    if current_times:
        current_times.sort()
        median_idx = len(current_times) // 2
        current_median = current_times[median_idx]
        median_str = _format_duration(current_median)
    else:
        current_median = None
        median_str = "N/A"

    if previous_times and current_median is not None:
        previous_times.sort()
        prev_median = previous_times[len(previous_times) // 2]
        if prev_median.total_seconds() > 0:
            med_pct = ((current_median.total_seconds() - prev_median.total_seconds()) / prev_median.total_seconds()) * 100
            wow_label = "w/w" if time_window_days == 7 else "m/m"
            # For resolution time, negative is GOOD (faster)
            sign = "+" if med_pct >= 0 else ""
            median_subtitle = f"{sign}{med_pct:.0f}% {wow_label}"
            median_sentiment = "positive" if med_pct <= 0 else "negative"
        else:
            median_subtitle = ""
            median_sentiment = "neutral"
    else:
        median_subtitle = ""
        median_sentiment = "neutral"

    # 3. % resolved within 1 week
    # Use ALL done issues (not just current period) for this metric
    all_times = [t for issue in done_issues if (t := _resolution_time(issue)) is not None]
    if all_times:
        within_week = sum(1 for t in all_times if t.total_seconds() <= 7 * 24 * 3600)
        pct_within_week = math.floor((within_week / len(all_times)) * 100)
        week_str = f"{pct_within_week}%"
    else:
        week_str = "N/A"

    return DashboardMetrics(
        time_window_days=time_window_days,
        issues_resolved=MetricCard(
            label=f"Issues Resolved ({period_label})",
            value=str(current_count),
            subtitle=resolved_subtitle,
            sentiment=resolved_sentiment,
        ),
        median_resolution_time=MetricCard(
            label="Median Resolution Time",
            value=median_str,
            subtitle=median_subtitle,
            sentiment=median_sentiment,
        ),
        resolved_within_one_week=MetricCard(
            label="Resolved Within 1 Week",
            value=week_str,
            subtitle="of all issues",
        ),
    )


async def compute_lists(settings: Settings) -> DashboardLists:
    """Compute the attention and in-progress lists.

    Attention: issues with devin:triaged, devin:pr-opened, devin:escalated
    In Progress: issues with devin:triage, devin:implement
    """
    repo = settings.target_repo
    token = settings.github_token

    async with httpx.AsyncClient() as client:
        attention_issues, progress_issues = await asyncio.gather(
            _fetch_issues_by_labels(
                client,
                repo,
                token,
                ["devin:triaged", "devin:pr-opened", "devin:escalated"],
            ),
            _fetch_issues_by_labels(
                client,
                repo,
                token,
                ["devin:triage", "devin:implement"],
            ),
        )

    needs_attention = [_issue_to_item(i) for i in attention_issues]
    in_progress = [_issue_to_item(i) for i in progress_issues]

    # Sort attention: escalated first, then pr-opened, then triaged
    status_priority = {
        "devin:escalated": 0,
        "devin:pr-opened": 1,
        "devin:triaged": 2,
    }
    needs_attention.sort(key=lambda x: status_priority.get(x.status_label, 99))

    return DashboardLists(
        needs_attention=needs_attention,
        in_progress=in_progress,
    )
