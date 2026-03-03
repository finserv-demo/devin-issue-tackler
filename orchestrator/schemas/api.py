"""API request/response schemas for the dashboard endpoints."""

from pydantic import BaseModel

# ── Issue list / detail ──


class TimelineEntry(BaseModel):
    """A single entry in the unified issue timeline."""

    type: str  # "comment" | "state_change" | "session_event" | "label"
    timestamp: str
    actor: str = ""
    body: str = ""
    from_state: str | None = None
    to_state: str | None = None
    label: str | None = None
    session_url: str | None = None


class SessionSummary(BaseModel):
    """Summary of a Devin session linked to an issue."""

    session_id: str
    stage: str  # "triage" | "implement"
    status: str  # "active" | "completed" | "failed"
    session_url: str = ""
    acus_consumed: float = 0.0
    created_at: str = ""


class IssueSummary(BaseModel):
    """Issue summary for the board listing."""

    number: int
    title: str
    state: str  # GitHub state: open/closed
    status: str  # Devin pipeline status: new, triage, triaged, implement, pr-opened, done, escalated
    sizing: str | None = None  # green, yellow, red
    labels: list[str] = []
    created_at: str = ""
    updated_at: str = ""
    time_in_state: str = ""  # human-readable duration
    html_url: str = ""
    pr_url: str | None = None
    needs_attention: bool = False
    attention_reason: str | None = None


class IssueDetail(BaseModel):
    """Full issue detail for the detail page."""

    number: int
    title: str
    body: str | None = None
    state: str
    status: str
    sizing: str | None = None
    labels: list[str] = []
    created_at: str = ""
    updated_at: str = ""
    html_url: str = ""
    pr_url: str | None = None
    pr_number: int | None = None
    needs_attention: bool = False
    attention_reason: str | None = None
    next_steps: str = ""
    timeline: list[TimelineEntry] = []
    sessions: list[SessionSummary] = []
    available_actions: list[str] = []  # "proceed", "close", "feedback"


# ── Commands & comments ──


class CommentRequest(BaseModel):
    """Request to post a comment on an issue."""

    body: str


class CommandRequest(BaseModel):
    """Request to execute a command on an issue."""

    action: str  # "proceed", "close", "feedback"
    message: str = ""


class CommandResponse(BaseModel):
    """Response from executing a command."""

    success: bool
    message: str


# ── Metrics ──


class PipelineCount(BaseModel):
    """Count of issues in each pipeline state."""

    state: str
    count: int
    color: str = ""


class ThroughputPoint(BaseModel):
    """A single data point in the throughput chart."""

    period: str  # e.g., "2026-W09"
    resolved: int
    opened: int


class ResolutionTimeStats(BaseModel):
    """Resolution time statistics."""

    median_hours: float
    mean_hours: float
    p90_hours: float
    total_resolved: int


class AcuSpendEntry(BaseModel):
    """ACU spend breakdown."""

    sizing: str  # green, yellow, red
    avg_acus: float
    total_acus: float
    issue_count: int


class MetricsSummary(BaseModel):
    """Combined metrics response."""

    pipeline: list[PipelineCount] = []
    throughput: list[ThroughputPoint] = []
    resolution_time: ResolutionTimeStats | None = None
    acu_spend: list[AcuSpendEntry] = []
    success_rate: float = 0.0  # percentage
    total_processed: int = 0
    total_done: int = 0
    total_escalated: int = 0


# ── Settings ──


class SettingsResponse(BaseModel):
    """Current system settings."""

    opt_out_label: str = "devin:skip"
    acu_limit_triage: int = 8
    acu_limit_implement: int = 50
    max_concurrent_implement: int = 10
    max_concurrent_total: int = 20
    polling_interval_seconds: int = 15
    bulk_triage_rate_limit: int = 5
    target_repo: str = ""


class SettingsUpdate(BaseModel):
    """Request to update settings."""

    opt_out_label: str | None = None
    acu_limit_triage: int | None = None
    acu_limit_implement: int | None = None
    max_concurrent_implement: int | None = None
    max_concurrent_total: int | None = None
    polling_interval_seconds: int | None = None
    bulk_triage_rate_limit: int | None = None
