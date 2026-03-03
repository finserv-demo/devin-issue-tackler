import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown hooks."""
    logger.info("Orchestrator starting up")
    # TODO: Start background poller (Phase 1, issue #10)
    yield
    logger.info("Orchestrator shutting down")


app = FastAPI(
    title="Finserv Backlog Automation",
    description="GitHub Issue Backlog Automation with Devin API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
