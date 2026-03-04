"""Vercel serverless function for GET /api/dashboard/metrics."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so that the orchestrator package
# is importable.  Vercel places the project at /var/task/ but only adds the
# function's own directory to sys.path, not the project root.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, Query  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from orchestrator.api.dashboard import compute_metrics  # noqa: E402
from orchestrator.config import Settings  # noqa: E402

app = FastAPI()


@app.get("/api/dashboard/metrics")
async def get_metrics(days: int = Query(default=7, enum=[7, 30])) -> dict:
    """Get hero metrics for the dashboard."""
    try:
        settings = Settings()
        if not settings.github_token:
            return JSONResponse(
                status_code=503,
                content={"error": "GITHUB_TOKEN environment variable is not set"},
            )
        result = await compute_metrics(settings, time_window_days=days)
        return result.model_dump()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
