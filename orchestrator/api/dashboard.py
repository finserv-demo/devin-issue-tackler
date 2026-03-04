"""Dashboard API endpoints.

Provides hero metrics and issue lists by querying the GitHub API
and Devin API. All data is fetched live — no local database.
"""

import asyncio
import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

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
        if name in ("devin:small", "devin:medium", "devin:large"):
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
            "devin:pr-in-progress",
            "devin:pr-ready",
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


async def _fetch_issue_timeline(
    client: httpx.AsyncClient,
    repo: str,
    token: str,
    issue_number: int,
) -> list[dict]:
    """Fetch timeline events for a single issue."""
    all_events: list[dict] = []
    page = 1
    while True:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{repo}/issues/{issue_number}/timeline",
            headers=_github_headers(token),
            params={"per_page": 100, "page": page},
            timeout=30.0,
        )
        resp.raise_for_status()
        items = resp.json()
        if not items:
            break
        all_events.extend(items)
        if len(items) < 100:
            break
        page += 1
    return all_events


async def _fetch_triage_start_times(
    client: httpx.AsyncClient,
    repo: str,
    token: str,
    issues: list[dict],
) -> dict[int, str | None]:
    """Fetch the devin:triage label timestamp for each issue, concurrently.

    Returns a dict mapping issue number -> ISO timestamp (or None if not found).
    """
    async def _get_triage_time(issue: dict) -> tuple[int, str | None]:
        number = issue["number"]
        try:
            events = await _fetch_issue_timeline(client, repo, token, number)
            return number, _find_label_added_time(events, "devin:triage")
        except httpx.HTTPStatusError:
            logger.warning("Failed to fetch timeline for issue #%d", number)
            return number, None

    results = await asyncio.gather(*[_get_triage_time(issue) for issue in issues])
    return dict(results)


def _format_duration(delta: timedelta) -> str:
    """Format a timedelta as a human-readable string like '2.3d' or '4.1h'."""
    total_hours = delta.total_seconds() / 3600
    if total_hours >= 24:
        days = total_hours / 24
        return f"{days:.1f}d"
    return f"{total_hours:.1f}h"


async def _find_linked_pr(
    client: httpx.AsyncClient,
    repo: str,
    token: str,
    issue_number: int,
) -> dict[str, Any] | None:
    """Find a PR that closes the given issue by searching PRs.

    Returns the PR dict (with number, html_url, head sha) or None.
    """
    try:
        events = await _fetch_issue_timeline(client, repo, token, issue_number)
        for event in events:
            # cross-referenced events from PRs that mention "Closes #N"
            if event.get("event") == "cross-referenced":
                source = event.get("source", {}).get("issue", {})
                if source.get("pull_request") and source.get("state") == "open":
                    pr_url = source["pull_request"].get("html_url", "")
                    # Fetch full PR to get head SHA
                    pr_resp = await client.get(
                        source["pull_request"]["url"],
                        headers=_github_headers(token),
                        timeout=30.0,
                    )
                    pr_resp.raise_for_status()
                    pr_data = pr_resp.json()
                    return {
                        "number": pr_data["number"],
                        "html_url": pr_url,
                        "head_sha": pr_data.get("head", {}).get("sha", ""),
                    }
    except httpx.HTTPStatusError:
        logger.warning("Failed to find linked PR for issue #%d", issue_number)
    return None


async def _fetch_ci_status(
    client: httpx.AsyncClient,
    repo: str,
    token: str,
    head_sha: str,
) -> str | None:
    """Fetch CI status for a commit SHA. Returns 'passing', 'failing', or 'pending'."""
    if not head_sha:
        return None
    try:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{repo}/commits/{head_sha}/check-runs",
            headers=_github_headers(token),
            timeout=30.0,
        )
        resp.raise_for_status()
        check_runs = resp.json().get("check_runs", [])
        if not check_runs:
            return "pending"

        has_failure = False
        has_pending = False
        for run in check_runs:
            status = run.get("status", "")
            conclusion = run.get("conclusion", "")
            if status != "completed":
                has_pending = True
            elif conclusion not in ("success", "skipped", "neutral"):
                has_failure = True

        if has_failure:
            return "failing"
        if has_pending:
            return "pending"
        return "passing"
    except httpx.HTTPStatusError:
        logger.warning("Failed to fetch CI status for %s", head_sha)
        return None


async def _fetch_unresolved_review_threads(
    client: httpx.AsyncClient,
    repo: str,
    token: str,
    pr_number: int,
) -> int | None:
    """Fetch count of unresolved review threads on a PR via GraphQL."""
    owner, name = repo.split("/", 1)
    query = """
    query($owner: String!, $name: String!, $number: Int!) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100) {
            nodes {
              isResolved
            }
          }
        }
      }
    }
    """
    try:
        resp = await client.post(
            "https://api.github.com/graphql",
            headers=_github_headers(token),
            json={
                "query": query,
                "variables": {"owner": owner, "name": name, "number": pr_number},
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        pr_data = (data.get("data") or {}).get("repository") or {}
        threads = (
            (pr_data.get("pullRequest") or {}).get("reviewThreads") or {}
        ).get("nodes", [])
        return sum(1 for t in threads if not t.get("isResolved", True))
    except (httpx.HTTPStatusError, KeyError, AttributeError):
        logger.warning("Failed to fetch review threads for PR #%d", pr_number)
        return None


async def _enrich_pr_issue(
    client: httpx.AsyncClient,
    repo: str,
    token: str,
    issue: dict,
) -> dict[str, Any]:
    """Fetch PR metadata for an issue in a PR stage.

    Returns a dict with pr_url, ci_status, and unresolved_review_threads.
    Catches all exceptions so a single issue's enrichment failure
    doesn't take down the entire /lists endpoint.
    """
    try:
        pr = await _find_linked_pr(client, repo, token, issue["number"])
        if pr is None:
            return {"pr_url": None, "ci_status": None, "unresolved_review_threads": None}

        ci_status, thread_count = await asyncio.gather(
            _fetch_ci_status(client, repo, token, pr["head_sha"]),
            _fetch_unresolved_review_threads(client, repo, token, pr["number"]),
        )

        return {
            "pr_url": pr["html_url"],
            "ci_status": ci_status,
            "unresolved_review_threads": thread_count,
        }
    except Exception:
        logger.warning("Failed to enrich PR data for issue #%d", issue.get("number", 0))
        return {"pr_url": None, "ci_status": None, "unresolved_review_threads": None}


def _issue_to_item(
    issue: dict,
    pr_enrichment: dict[str, Any] | None = None,
) -> IssueItem:
    """Convert a GitHub issue dict to an IssueItem."""
    labels = issue.get("labels", [])
    status_label = _extract_status(labels)

    # Compute time_in_state from issue updated_at as a fallback
    updated = issue.get("updated_at", "")
    time_in_state = _time_ago(updated) if updated else ""

    pr_url = None
    ci_status = None
    unresolved_review_threads = None
    if pr_enrichment:
        pr_url = pr_enrichment.get("pr_url")
        ci_status = pr_enrichment.get("ci_status")
        unresolved_review_threads = pr_enrichment.get("unresolved_review_threads")

    return IssueItem(
        number=issue["number"],
        title=issue["title"],
        html_url=issue.get("html_url", ""),
        status_label=status_label,
        sizing_label=_extract_sizing(labels),
        time_in_state=time_in_state,
        pr_url=pr_url,
        ci_status=ci_status,
        unresolved_review_threads=unresolved_review_threads,
        created_at=issue.get("created_at", ""),
    )


# ── Metrics computation ──


async def compute_metrics(settings: Settings, time_window_days: int = 7) -> DashboardMetrics:
    """Compute hero metrics for the dashboard.

    Fetches closed issues with devin:done label and computes:
    1. Issues resolved in current period + w/w change
    2. Median time to resolution (from devin:triage label → close) + w/w change
    3. % resolved within 1 week of triage

    Resolution time is measured from when the devin:triage label was applied
    (fetched via timeline events) to when the issue was closed. Falls back to
    created_at if the triage label event is not found.
    """
    repo = settings.target_repo
    token = settings.github_token

    now = datetime.now(UTC)
    current_start = now - timedelta(days=time_window_days)
    previous_start = current_start - timedelta(days=time_window_days)

    async with httpx.AsyncClient() as client:
        # Fetch all closed issues with devin:done
        done_issues = await _fetch_issues_by_label(client, repo, token, "devin:done", state="closed")

        # Fetch when devin:triage was applied to each issue (timer start)
        triage_times = await _fetch_triage_start_times(client, repo, token, done_issues)

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

    # 2. Median time to resolution (from devin:triage label → closed_at)
    def _resolution_time(issue: dict) -> timedelta | None:
        # Use the devin:triage label timestamp as the start time.
        # Fall back to created_at if the triage label was never found.
        triage_time_str = triage_times.get(issue["number"])
        start = triage_time_str or issue.get("created_at", "")
        closed = issue.get("closed_at", "")
        if not start or not closed:
            return None
        try:
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            d = datetime.fromisoformat(closed.replace("Z", "+00:00"))
            return d - s
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
            label=f"Median Resolution Time ({period_label})",
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


def _is_pr_stage(issue: dict) -> bool:
    """Check if an issue is in a PR stage (pr-in-progress or pr-ready)."""
    labels = issue.get("labels", [])
    for label in labels:
        name = label.get("name", "")
        if name in ("devin:pr-in-progress", "devin:pr-ready"):
            return True
    return False


async def compute_lists(settings: Settings) -> DashboardLists:
    """Compute the attention and in-progress lists.

    Attention: issues with devin:triaged, devin:pr-ready, devin:escalated
    In Progress: issues with devin:triage, devin:implement, devin:pr-in-progress

    For issues in PR stages, enriches with linked PR URL, CI status,
    and unresolved review thread count.
    """
    repo = settings.target_repo
    token = settings.github_token

    async with httpx.AsyncClient() as client:
        attention_issues, progress_issues = await asyncio.gather(
            _fetch_issues_by_labels(
                client,
                repo,
                token,
                ["devin:triaged", "devin:pr-ready", "devin:escalated"],
            ),
            _fetch_issues_by_labels(
                client,
                repo,
                token,
                ["devin:triage", "devin:implement", "devin:pr-in-progress"],
            ),
        )

        # Enrich PR-stage issues with PR metadata (concurrently)
        all_issues = attention_issues + progress_issues
        pr_stage_issues = [i for i in all_issues if _is_pr_stage(i)]

        enrichment_results = await asyncio.gather(
            *[
                _enrich_pr_issue(client, repo, token, issue)
                for issue in pr_stage_issues
            ]
        )
        enrichment_map: dict[int, dict[str, Any]] = {
            issue["number"]: result
            for issue, result in zip(pr_stage_issues, enrichment_results, strict=True)
        }

    needs_attention = [
        _issue_to_item(i, enrichment_map.get(i["number"])) for i in attention_issues
    ]
    in_progress = [
        _issue_to_item(i, enrichment_map.get(i["number"])) for i in progress_issues
    ]

    # Sort attention: escalated first, then pr-ready, then triaged
    status_priority = {
        "devin:escalated": 0,
        "devin:pr-ready": 1,
        "devin:triaged": 2,
    }
    needs_attention.sort(key=lambda x: status_priority.get(x.status_label, 99))

    return DashboardLists(
        needs_attention=needs_attention,
        in_progress=in_progress,
    )
