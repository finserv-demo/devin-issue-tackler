from pydantic import BaseModel


class DevinSession(BaseModel):
    """Parsed Devin API session."""

    session_id: str
    url: str = ""
    status: str = "new"
    acus_consumed: float = 0.0
    created_at: int = 0
    updated_at: int = 0
    tags: list[str] = []
    pull_requests: list[dict] = []


class Message(BaseModel):
    """A single message from the Devin session."""

    event_id: str = ""
    source: str = ""  # "user" or "devin"
    message: str = ""
    created_at: int = 0


class MessagePage(BaseModel):
    """Paginated message response from Devin API."""

    items: list[Message] = []
    has_next_page: bool = False
    end_cursor: str | None = None


class Playbook(BaseModel):
    """Parsed Devin playbook."""

    playbook_id: str
    title: str = ""
    body: str = ""
    status: str = ""
