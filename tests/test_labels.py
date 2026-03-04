from orchestrator.labels import (
    LABEL_DEFINITIONS,
    VALID_TRANSITIONS,
    DevinControl,
    DevinSizing,
    DevinStatus,
    get_current_status,
    get_session_stage,
    is_valid_transition,
)

# ── Valid transitions ──


def test_valid_transition_none_to_triage() -> None:
    assert is_valid_transition(None, DevinStatus.TRIAGE) is True


def test_valid_transition_triage_to_triaged() -> None:
    assert is_valid_transition(DevinStatus.TRIAGE, DevinStatus.TRIAGED) is True


def test_valid_transition_triaged_to_implement() -> None:
    assert is_valid_transition(DevinStatus.TRIAGED, DevinStatus.IMPLEMENT) is True


def test_valid_transition_triaged_to_triage() -> None:
    assert is_valid_transition(DevinStatus.TRIAGED, DevinStatus.TRIAGE) is True


def test_valid_transition_implement_to_pr_opened() -> None:
    assert is_valid_transition(DevinStatus.IMPLEMENT, DevinStatus.PR_OPENED) is True


def test_valid_transition_implement_to_escalated() -> None:
    assert is_valid_transition(DevinStatus.IMPLEMENT, DevinStatus.ESCALATED) is True


def test_valid_transition_pr_opened_to_done() -> None:
    assert is_valid_transition(DevinStatus.PR_OPENED, DevinStatus.DONE) is True


def test_valid_transition_pr_opened_to_escalated() -> None:
    assert is_valid_transition(DevinStatus.PR_OPENED, DevinStatus.ESCALATED) is True


def test_valid_transition_pr_opened_to_triaged() -> None:
    """PR closed without merge should allow transitioning back to triaged."""
    assert is_valid_transition(DevinStatus.PR_OPENED, DevinStatus.TRIAGED) is True


def test_valid_transition_escalated_to_triage() -> None:
    assert is_valid_transition(DevinStatus.ESCALATED, DevinStatus.TRIAGE) is True


def test_valid_transition_escalated_to_implement() -> None:
    assert is_valid_transition(DevinStatus.ESCALATED, DevinStatus.IMPLEMENT) is True


# ── Invalid transitions ──


def test_invalid_transition_none_to_implement() -> None:
    assert is_valid_transition(None, DevinStatus.IMPLEMENT) is False


def test_invalid_transition_triage_to_implement() -> None:
    assert is_valid_transition(DevinStatus.TRIAGE, DevinStatus.IMPLEMENT) is False


def test_invalid_transition_done_to_anything() -> None:
    for status in DevinStatus:
        assert is_valid_transition(DevinStatus.DONE, status) is False


def test_invalid_transition_unknown_from_state() -> None:
    assert is_valid_transition("unknown:label", DevinStatus.TRIAGE) is False


# ── get_current_status ──


def test_get_current_status_with_triage_label() -> None:
    labels = ["bug", "devin:triage", "priority:high"]
    assert get_current_status(labels) == DevinStatus.TRIAGE


def test_get_current_status_with_implement_label() -> None:
    labels = ["devin:implement", "devin:yellow"]
    assert get_current_status(labels) == DevinStatus.IMPLEMENT


def test_get_current_status_with_done_label() -> None:
    labels = ["devin:done"]
    assert get_current_status(labels) == DevinStatus.DONE


def test_get_current_status_with_no_devin_status() -> None:
    labels = ["bug", "enhancement", "devin:green"]
    assert get_current_status(labels) is None


def test_get_current_status_empty_labels() -> None:
    assert get_current_status([]) is None


# ── get_session_stage ──


def test_get_session_stage_triage() -> None:
    assert get_session_stage(DevinStatus.TRIAGE) == "triage"


def test_get_session_stage_implement() -> None:
    assert get_session_stage(DevinStatus.IMPLEMENT) == "implement"


def test_get_session_stage_non_trigger() -> None:
    assert get_session_stage(DevinStatus.TRIAGED) is None


def test_get_session_stage_unknown() -> None:
    assert get_session_stage("not-a-label") is None


# ── Label definitions ──


def test_all_labels_have_colors() -> None:
    """Every status, sizing, and control label must have a color definition."""
    all_labels = [s.value for s in DevinStatus] + [s.value for s in DevinSizing] + [s.value for s in DevinControl]
    for label in all_labels:
        assert label in LABEL_DEFINITIONS, f"Missing color for {label}"
        color = LABEL_DEFINITIONS[label]
        assert len(color) == 6, f"Color for {label} should be 6 hex chars, got {color}"


def test_all_status_labels_in_valid_transitions() -> None:
    """Every DevinStatus value should appear as a key in VALID_TRANSITIONS."""
    for status in DevinStatus:
        assert status in VALID_TRANSITIONS, f"Missing transitions for {status}"


def test_label_definition_count() -> None:
    """Should have exactly 10 label definitions (6 status + 3 sizing + 1 control)."""
    assert len(LABEL_DEFINITIONS) == 10
