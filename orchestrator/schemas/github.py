from pydantic import BaseModel


class GitHubIssue(BaseModel):
    """Parsed GitHub issue."""

    number: int
    title: str
    body: str | None = None
    labels: list[str] = []
    state: str = "open"
    created_at: str = ""
    updated_at: str = ""
    html_url: str = ""


class GitHubComment(BaseModel):
    """Parsed GitHub issue comment."""

    id: int
    author: str = ""
    body: str = ""
    created_at: str = ""


class TimelineEvent(BaseModel):
    """Parsed GitHub timeline event (label changes, etc.)."""

    event: str = ""
    label: str | None = None
    created_at: str = ""
    actor: str = ""


class PullRequest(BaseModel):
    """Parsed GitHub pull request."""

    number: int
    title: str = ""
    state: str = "open"
    html_url: str = ""
    merged_at: str | None = None
