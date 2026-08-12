"""Tests for explicit developer repair authorization boundaries."""
from __future__ import annotations

import pytest

from .developer_repair_contracts import AccessState, RepairProposal, RepairState


def _proposal(*, access: AccessState = AccessState.NOT_REQUESTED) -> RepairProposal:
    return RepairProposal(
        proposal_id="repair-001",
        problem="Dependency installation failed",
        cause="Package resolution failure",
        explanation="The declared dependency set could not be resolved.",
        fix="Resolve the dependency conflict and rerun validation.",
        scope=("pyproject.toml", "CI"),
        risk="May change build dependency resolution.",
        access=access,
    )


def test_proposal_starts_proposed() -> None:
    assert _proposal().state is RepairState.PROPOSED


def test_owner_authorization_changes_state() -> None:
    proposal = _proposal(access=AccessState.AVAILABLE)
    authorized = proposal.authorize()
    assert authorized.state is RepairState.AUTHORIZED
    assert authorized.proposal_id == proposal.proposal_id
    assert authorized.scope == proposal.scope


def test_denied_access_cannot_be_authorized() -> None:
    proposal = _proposal(access=AccessState.DENIED)
    with pytest.raises(PermissionError, match="access is denied"):
        proposal.authorize()


def test_decline_never_executes() -> None:
    declined = _proposal(access=AccessState.AVAILABLE).decline()
    assert declined.state is RepairState.DECLINED


def test_proposal_cannot_start_authorized() -> None:
    with pytest.raises(ValueError, match="start in PROPOSED"):
        RepairProposal(
            proposal_id="repair-002",
            problem="x",
            cause="y",
            explanation="z",
            fix="f",
            scope=("file",),
            risk="low",
            state=RepairState.AUTHORIZED,
        )
