"""Dashboard API: Metrics endpoints.

These endpoints serve aggregated metrics for the dashboard.
In Phase 3, they return mock data matching the real schema.
"""

from fastapi import APIRouter

from orchestrator.schemas.api import (
    AcuSpendEntry,
    MetricsSummary,
    PipelineCount,
    ResolutionTimeStats,
    ThroughputPoint,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


# Pipeline progression colors — earlier stages are cooler, later stages warmer.
# Escalated is red (needs help), skipped is neutral gray.
_PIPELINE_COLORS: dict[str, str] = {
    "triage": "#3b82f6",     # blue — early analysis
    "triaged": "#0ea5e9",    # teal — analyzed, awaiting action
    "implement": "#6366f1",  # indigo — active work
    "pr-opened": "#f59e0b",  # amber — nearly done, awaiting review
    "escalated": "#dc2626",  # red — needs human help
    "skipped": "#9ca3af",    # gray — opted out
}

# Map pipeline state → GitHub label for building filter URLs
_STATE_LABELS: dict[str, str] = {
    "triage": "devin:triage",
    "triaged": "devin:triaged",
    "implement": "devin:implement",
    "pr-opened": "devin:pr-opened",
    "escalated": "devin:escalated",
    "skipped": "devin:skip",
}

_TARGET_REPO = "finserv-demo/finserv"


def _github_label_url(label: str) -> str:
    """Build a GitHub issues URL filtered to a single label."""
    from urllib.parse import quote
    return f"https://github.com/{_TARGET_REPO}/issues?q=is%3Aissue+is%3Aopen+label%3A{quote(label, safe='')}"


@router.get("/summary")
async def get_metrics_summary() -> MetricsSummary:
    """Get combined metrics summary for the dashboard."""
    # Only in-flight stages + skipped — not new (untouched) or done (resolved).
    pipeline_states = ["triage", "triaged", "implement", "pr-opened", "escalated", "skipped"]
    pipeline_counts: dict[str, int] = {
        "triage": 1,
        "triaged": 2,
        "implement": 2,
        "pr-opened": 2,
        "escalated": 1,
        "skipped": 1,
    }
    pipeline = [
        PipelineCount(
            state=state,
            count=pipeline_counts[state],
            color=_PIPELINE_COLORS[state],
            label=_STATE_LABELS[state],
            github_filter_url=_github_label_url(_STATE_LABELS[state]),
        )
        for state in pipeline_states
    ]

    throughput = [
        ThroughputPoint(period="2026-W05", resolved=2, opened=5),
        ThroughputPoint(period="2026-W06", resolved=4, opened=3),
        ThroughputPoint(period="2026-W07", resolved=6, opened=4),
        ThroughputPoint(period="2026-W08", resolved=5, opened=2),
        ThroughputPoint(period="2026-W09", resolved=3, opened=1),
    ]

    resolution_time = ResolutionTimeStats(
        median_hours=18.5,
        mean_hours=24.2,
        p90_hours=48.0,
        total_resolved=20,
    )

    acu_spend = [
        AcuSpendEntry(sizing="green", avg_acus=8.5, total_acus=68.0, issue_count=8),
        AcuSpendEntry(sizing="yellow", avg_acus=22.0, total_acus=110.0, issue_count=5),
        AcuSpendEntry(sizing="red", avg_acus=42.0, total_acus=84.0, issue_count=2),
    ]

    return MetricsSummary(
        pipeline=pipeline,
        throughput=throughput,
        resolution_time=resolution_time,
        acu_spend=acu_spend,
        success_rate=85.0,
        total_processed=20,
        total_done=17,
        total_escalated=3,
    )
