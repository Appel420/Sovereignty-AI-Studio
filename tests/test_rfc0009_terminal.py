from dataclasses import dataclass

import pytest

from rfc0009 import ValidationError
from rfc0009.validators import validate_terminal_resolution


@dataclass(frozen=True)
class TransitionRecord:
    sequence: int
    previous: str
    current: str


def test_incomplete_execution_requires_marker():
    records = [TransitionRecord(1, "INITIALIZED", "RUNNING")]

    with pytest.raises(
        ValidationError,
        match="execution incomplete without explicit incomplete marker",
    ):
        validate_terminal_resolution(records)


def test_explicit_incomplete_marker_is_terminal_failure():
    records = [TransitionRecord(1, "RUNNING", "INCOMPLETE")]

    assert validate_terminal_resolution(records) == "failure"
