"""Terminal lifecycle validation."""

from collections.abc import Sequence
from typing import Protocol

from ..core import SUCCESS_TERMINAL, TERMINAL_STATES, ValidationError


class Transition(Protocol):
    """The terminal state portion of a transition record."""

    current: str


def validate_terminal_resolution(records: Sequence[Transition]) -> str:
    """Classify an explicit terminal state or reject incomplete execution."""
    if not records:
        raise ValidationError("empty history")

    terminal = records[-1].current
    if terminal == SUCCESS_TERMINAL:
        return "success"
    if terminal in TERMINAL_STATES:
        return "failure"
    raise ValidationError("execution incomplete without explicit incomplete marker")
