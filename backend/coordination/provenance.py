"""Explicit provenance contracts for local coordination decisions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceSource(StrEnum):
    """Origin of evidence attached to a coordination decision."""

    LOCAL = "local"
    TEST = "test"


class ExecutionMode(StrEnum):
    """Execution boundary under which evidence was produced."""

    LOCAL = "local"
    TEST = "test"


@dataclass(frozen=True, slots=True)
class Provenance:
    """Minimal immutable provenance record exposed by coordination APIs."""

    source: EvidenceSource
    execution_mode: ExecutionMode
    description: str = ""


TEST_PROVENANCE = Provenance(
    source=EvidenceSource.TEST,
    execution_mode=ExecutionMode.TEST,
    description="test provenance",
)
