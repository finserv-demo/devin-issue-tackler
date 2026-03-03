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


# Colors matching the frontend STATUS_CONFIG for visual consistency
_STATE_COLORS: dict[str, str] = {
    "new": "#6b7280",
    "triage": "#1d76db",
    "triaged": "#0e8a16",
    "implement": "#5319e7",
    "pr-opened": "#b45309",
    "done": "#15803d",
    "escalated": "#dc2626",
}


@router.get("/summary")
async def get_metrics_summary() -> MetricsSummary:
    """Get combined metrics summary for the dashboard."""
    pipeline = [
        PipelineCount(state="new", count=1, color=_STATE_COLORS["new"]),
        PipelineCount(state="triage", count=1, color=_STATE_COLORS["triage"]),
        PipelineCount(state="triaged", count=2, color=_STATE_COLORS["triaged"]),
        PipelineCount(state="implement", count=2, color=_STATE_COLORS["implement"]),
        PipelineCount(state="pr-opened", count=2, color=_STATE_COLORS["pr-opened"]),
        PipelineCount(state="done", count=3, color=_STATE_COLORS["done"]),
        PipelineCount(state="escalated", count=1, color=_STATE_COLORS["escalated"]),
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
