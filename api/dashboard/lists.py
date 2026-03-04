"""Vercel serverless function for GET /api/dashboard/lists."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so that the orchestrator package
# is importable.  Vercel places the project at /var/task/ but only adds the
# function's own directory to sys.path, not the project root.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from orchestrator.api.dashboard import compute_lists  # noqa: E402
from orchestrator.config import Settings  # noqa: E402

app = FastAPI()


@app.get("/api/dashboard/lists")
async def get_lists() -> dict:
    """Get the needs-attention and in-progress issue lists."""
    try:
        settings = Settings()
        if not settings.github_token:
            return JSONResponse(
                status_code=503,
                content={"error": "GITHUB_TOKEN environment variable is not set"},
            )
        result = await compute_lists(settings)
        return result.model_dump()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
