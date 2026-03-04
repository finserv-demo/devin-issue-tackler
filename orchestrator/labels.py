from enum import StrEnum


class DevinStatus(StrEnum):
    """Mutually exclusive status labels — one at a time per issue."""

    TRIAGE = "devin:triage"
    TRIAGED = "devin:triaged"
    IMPLEMENT = "devin:implement"
    PR_IN_PROGRESS = "devin:pr-in-progress"
    PR_READY = "devin:pr-ready"
    DONE = "devin:done"
    ESCALATED = "devin:escalated"


class DevinSizing(StrEnum):
    """Informational sizing labels — persists for issue lifetime."""

    SMALL = "devin:small"  # <2 hours junior engineer effort
    MEDIUM = "devin:medium"  # 2-8 hours, single service
    LARGE = "devin:large"  # >1 day, multiple services


class DevinControl(StrEnum):
    """Control labels."""

    SKIP = "devin:skip"


# Labels that trigger a new Devin session
SESSION_TRIGGER_LABELS: dict[str, str] = {
    DevinStatus.TRIAGE: "triage",
    DevinStatus.IMPLEMENT: "implement",
}

# Valid state transitions: from_state -> list of valid to_states
VALID_TRANSITIONS: dict[str | None, list[DevinStatus]] = {
    None: [DevinStatus.TRIAGE],
    DevinStatus.TRIAGE: [DevinStatus.TRIAGED],
    DevinStatus.TRIAGED: [DevinStatus.IMPLEMENT, DevinStatus.TRIAGE],
    DevinStatus.IMPLEMENT: [DevinStatus.PR_IN_PROGRESS, DevinStatus.ESCALATED],
    DevinStatus.PR_IN_PROGRESS: [DevinStatus.PR_READY, DevinStatus.ESCALATED, DevinStatus.TRIAGED],
    DevinStatus.PR_READY: [DevinStatus.PR_IN_PROGRESS, DevinStatus.DONE, DevinStatus.ESCALATED, DevinStatus.TRIAGED],
    DevinStatus.ESCALATED: [DevinStatus.TRIAGE, DevinStatus.IMPLEMENT],
    DevinStatus.DONE: [],
}

# Label colors for GitHub (hex without #)
LABEL_DEFINITIONS: dict[str, str] = {
    "devin:triage": "1d76db",
    "devin:triaged": "0e8a16",
    "devin:implement": "5319e7",
    "devin:pr-in-progress": "f9d0c4",
    "devin:pr-ready": "0e8a16",
    "devin:done": "0e8a16",
    "devin:escalated": "d93f0b",
    "devin:small": "c5f015",
    "devin:medium": "fbca04",
    "devin:large": "d93f0b",
    "devin:skip": "cccccc",
}


def is_valid_transition(from_state: str | None, to_state: str) -> bool:
    """Check if a state transition is valid.

    Args:
        from_state: Current devin status label (or None if no status label).
        to_state: Target devin status label.

    Returns:
        True if the transition is valid.
    """
    valid_targets = VALID_TRANSITIONS.get(from_state, [])
    return to_state in valid_targets


def get_current_status(labels: list[str]) -> DevinStatus | None:
    """Extract the current devin status label from a list of labels.

    Args:
        labels: List of all labels on an issue.

    Returns:
        The current DevinStatus, or None if no status label is present.
    """
    status_values = set(s.value for s in DevinStatus)
    for label in labels:
        if label in status_values:
            return DevinStatus(label)
    return None


def get_session_stage(label: str) -> str | None:
    """If this label triggers a Devin session, return the stage name.

    Args:
        label: A label string.

    Returns:
        Stage name ("triage" or "implement"), or None if not a trigger label.
    """
    return SESSION_TRIGGER_LABELS.get(label)
