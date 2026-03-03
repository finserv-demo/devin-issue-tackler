"""GitHub webhook receiver and event router.

Receives GitHub webhooks, verifies HMAC-SHA256 signatures, and dispatches
events to the appropriate handler functions. This is a thin event router —
it parses events and dispatches, but contains no business logic.
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Request

from orchestrator.config import Settings
from orchestrator.devin_client import DevinClient
from orchestrator.github_client import GitHubClient
from orchestrator.handlers.commands import handle_comment
from orchestrator.handlers.implement import handle_implement
from orchestrator.handlers.triage import handle_triage
from orchestrator.labels import DevinControl, DevinStatus, get_current_status

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> None:
    """Verify GitHub webhook HMAC-SHA256 signature.

    Args:
        payload_body: Raw request body bytes.
        signature_header: Value of X-Hub-Signature-256 header.
        secret: Webhook secret configured in GitHub.

    Raises:
        HTTPException: If signature is invalid.
    """
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


def _make_clients(settings: Settings) -> tuple[GitHubClient, DevinClient]:
    """Create GitHub and Devin clients from settings."""
    github = GitHubClient(token=settings.github_token, repo=settings.target_repo)
    devin = DevinClient(api_key=settings.devin_api_key, org_id=settings.devin_org_id)
    return github, devin


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(...),
    x_github_event: str = Header(...),
) -> dict[str, str]:
    """Receive GitHub webhooks, verify signature, and dispatch to handlers."""
    settings = Settings()
    body = await request.body()
    verify_signature(body, x_hub_signature_256, settings.github_webhook_secret)

    payload = await request.json()
    github, devin = _make_clients(settings)

    match x_github_event:
        case "issues":
            action = payload.get("action")
            if action == "opened":
                await on_issue_opened(payload, github, settings)
            elif action == "labeled":
                await on_issue_labeled(payload, github, devin, settings)
            elif action == "closed":
                await on_issue_closed(payload, github, devin)
            elif action == "reopened":
                await on_issue_reopened(payload)
        case "issue_comment":
            if payload.get("action") == "created":
                await on_issue_comment(payload, github, devin, settings)

    return {"status": "ok"}


async def on_issue_opened(
    payload: dict,
    github: GitHubClient,
    settings: Settings,
) -> None:
    """New issue -> add devin:triage label (unless opted out)."""
    issue = payload.get("issue", {})
    issue_number: int = issue.get("number", 0)
    labels = [label.get("name", "") for label in issue.get("labels", [])]

    logger.info("Issue #%d opened: %s", issue_number, issue.get("title", ""))

    if settings.opt_out_label in labels:
        logger.info("Issue #%d has %s label, skipping triage", issue_number, settings.opt_out_label)
        return

    # Check if already has a devin status label (shouldn't happen on open, but be safe)
    if get_current_status(labels) is not None:
        logger.info("Issue #%d already has a devin status label, skipping", issue_number)
        return

    await github.add_label(issue_number, DevinStatus.TRIAGE)


async def on_issue_labeled(
    payload: dict,
    github: GitHubClient,
    devin: DevinClient,
    settings: Settings,
) -> None:
    """Label added -> create corresponding Devin session if it's a trigger label."""
    issue = payload.get("issue", {})
    issue_number: int = issue.get("number", 0)
    label_name: str = payload.get("label", {}).get("name", "")

    logger.info("Issue #%d labeled with %r", issue_number, label_name)

    if label_name == DevinStatus.TRIAGE:
        await handle_triage(issue_number, github, devin, settings)
    elif label_name == DevinStatus.IMPLEMENT:
        await handle_implement(issue_number, github, devin, settings)
    else:
        logger.debug("Label %r is not a session trigger, ignoring", label_name)


async def on_issue_comment(
    payload: dict,
    github: GitHubClient,
    devin: DevinClient,
    settings: Settings,
) -> None:
    """Comment on issue -> check for slash commands or forward to active session."""
    issue = payload.get("issue", {})
    issue_number: int = issue.get("number", 0)
    comment = payload.get("comment", {})
    author: str = comment.get("user", {}).get("login", "")
    body: str = comment.get("body", "")

    logger.info("Comment on issue #%d by %s", issue_number, author)

    await handle_comment(issue_number, author, body, github, devin, settings)


async def on_issue_closed(
    payload: dict,
    github: GitHubClient,
    devin: DevinClient,
) -> None:
    """Issue closed externally -> terminate active session and clean up."""
    issue = payload.get("issue", {})
    issue_number: int = issue.get("number", 0)
    labels = [label.get("name", "") for label in issue.get("labels", [])]

    logger.info("Issue #%d closed", issue_number)

    current_status = get_current_status(labels)
    if current_status is not None and current_status not in (DevinStatus.DONE, DevinControl.SKIP):
        # Terminate any active session
        active_session = await devin.get_active_session_for_issue(issue_number)
        if active_session:
            try:
                await devin.terminate_session(active_session.session_id)
                logger.info("Terminated session %s for closed issue #%d", active_session.session_id, issue_number)
            except Exception:
                logger.exception("Failed to terminate session for issue #%d", issue_number)


async def on_issue_reopened(payload: dict) -> None:
    """Issue reopened -> log the event (no automatic action)."""
    issue = payload.get("issue", {})
    issue_number: int = issue.get("number", 0)
    logger.info("Issue #%d reopened", issue_number)
