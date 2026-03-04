"""Vercel serverless function for GET /api/dashboard/lists."""

from fastapi import FastAPI

from orchestrator.api.dashboard import compute_lists
from orchestrator.config import Settings

app = FastAPI()


@app.get("/api/dashboard/lists")
async def get_lists() -> dict:
    """Get the needs-attention and in-progress issue lists."""
    settings = Settings()
    result = await compute_lists(settings)
    return result.model_dump()
