"""Dashboard API routes."""

from fastapi import APIRouter, Query

from orchestrator.api.dashboard import compute_lists, compute_metrics
from orchestrator.config import Settings
from orchestrator.schemas.dashboard import DashboardLists, DashboardMetrics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_settings = Settings()


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(days: int = Query(default=7, ge=7, le=30)) -> DashboardMetrics:
    """Get hero metrics for the dashboard.

    Args:
        days: Time window in days (7 or 30).
    """
    return await compute_metrics(_settings, time_window_days=days)


@router.get("/lists", response_model=DashboardLists)
async def get_lists() -> DashboardLists:
    """Get the needs-attention and in-progress issue lists."""
    return await compute_lists(_settings)
