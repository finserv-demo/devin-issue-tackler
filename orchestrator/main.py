import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from orchestrator.config import Settings
from orchestrator.devin_client import DevinClient
from orchestrator.github_client import GitHubClient
from orchestrator.poller import SessionPoller
from orchestrator.webhooks import router as webhook_router

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown hooks."""
    logger.info("Orchestrator starting up")

    settings = Settings()
    github = GitHubClient(token=settings.github_token, repo=settings.target_repo)
    devin = DevinClient(api_key=settings.devin_api_key, org_id=settings.devin_org_id)

    # Discover our own GitHub identity so we can ignore our own comments
    try:
        bot_login = await github.get_authenticated_user()
        logger.info("Authenticated as GitHub user: %s", bot_login)
    except Exception:
        bot_login = None
        logger.warning("Could not determine GitHub identity; mirrored comments may echo back")
    _app.state.bot_login = bot_login

    poller = SessionPoller(github=github, devin=devin, settings=settings)
    _app.state.poller = poller

    # Start poller as background task
    poller_task = asyncio.create_task(poller.run_forever())

    yield

    logger.info("Orchestrator shutting down")
    poller_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await poller_task


app = FastAPI(
    title="Finserv Backlog Automation",
    description="GitHub Issue Backlog Automation with Devin API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhook_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
