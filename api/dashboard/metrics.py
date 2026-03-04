"""Vercel serverless function for GET /api/dashboard/metrics."""

from fastapi import FastAPI, Query

from orchestrator.api.dashboard import compute_metrics
from orchestrator.config import Settings

app = FastAPI()


@app.get("/api/dashboard/metrics")
async def get_metrics(days: int = Query(default=7, enum=[7, 30])) -> dict:
    """Get hero metrics for the dashboard."""
    settings = Settings()
    result = await compute_metrics(settings, time_window_days=days)
    return result.model_dump()
