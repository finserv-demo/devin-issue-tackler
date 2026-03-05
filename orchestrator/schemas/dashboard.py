"""Dashboard API response schemas."""

from pydantic import BaseModel


class MetricCard(BaseModel):
    """A single hero metric card."""

    label: str
    value: str
    subtitle: str = ""  # e.g. "+12% w/w" or "-5% w/w"
    sentiment: str = "neutral"  # "positive", "negative", or "neutral"
    link_url: str = ""  # optional URL to navigate to when the card is clicked


class SizeMetricBreakdown(BaseModel):
    """All 3 metrics computed for a single size bucket (or overall)."""

    size_label: str | None = None  # None = "overall", else "devin:small" / "devin:medium" / "devin:large"
    display_name: str  # "Overall", "Small", "Medium", "Large"
    issues_resolved: MetricCard
    median_resolution_time: MetricCard
    resolved_within_one_week: MetricCard


class DashboardMetrics(BaseModel):
    """Hero metrics for the dashboard."""

    time_window_days: int  # 7 or 30
    issues_resolved: MetricCard
    median_resolution_time: MetricCard
    resolved_within_one_week: MetricCard
    breakdowns: list[SizeMetricBreakdown] = []  # per-size + overall breakdown for metrics page


class IssueItem(BaseModel):
    """An issue/PR in the attention or in-progress lists."""

    number: int
    title: str
    html_url: str  # GitHub issue URL
    status_label: str  # e.g. "devin:triaged", "devin:pr-ready"
    sizing_label: str | None = None  # e.g. "devin:small", "devin:medium", "devin:large"
    time_in_state: str = ""  # e.g. "2h ago", "3d ago"
    pr_url: str | None = None  # For pr-ready/pr-in-progress issues, link to the PR
    ci_status: str | None = None  # "passing" | "failing" | "pending" | None
    unresolved_review_threads: int | None = None  # Count of unresolved review threads
    created_at: str = ""
    updated_at: str = ""
    acus_consumed: float | None = None
    devin_latest_message: str | None = None


class DashboardLists(BaseModel):
    """The two lists for the dashboard."""

    needs_attention: list[IssueItem]
    in_progress: list[IssueItem]
