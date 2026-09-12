from __future__ import annotations

import base64
import hashlib

from backend.coordination.merge_authorization import (
    canonical_authorization_message,
    sha256_canonical,
    validate_authorization_history,
    verify_authorization,
)


def _proposal() -> dict[str, str]:
    return {
        "source_sha": "abc123",
        "target_branch": "main",
        "agent_id": "GPT/Codex",
        "files": ["backend/coordination/merge_authorization.py"],
    }


def _authorization(proposal: dict[str, str], signature: bytes = b"valid") -> dict[str, object]:
    authorization: dict[str, object] = {
        "event": "merge_authorized",
        "event_version": 1,
        "proposal_sha": sha256_canonical(proposal),
        "source_sha": proposal["source_sha"],
        "target_branch": proposal["target_branch"],
        "approved_by": "human-owner",
        "approval_method": "protected-branch-review",
        "signer_key_id": "owner-key-2026-01",
        "signature_scheme": "ML-DSA-65",
        "signature": "base64url:" + base64.urlsafe_b64encode(signature).decode().rstrip("="),
        "timestamp": "2026-09-02T12:00:00Z",
    }
    return authorization


def _verify(scheme: str, public_key: bytes, message: bytes, signature: bytes) -> bool:
    expected = hashlib.sha256(public_key + canonical_authorization_message(_authorization(_proposal()))).digest()
    return scheme == "ML-DSA-65" and signature == b"valid" and message.startswith(b"SCAR/MERGE_AUTHORIZATION/v1\n") and expected


def test_valid_owner_authorization_is_bound_to_proposal_and_branch() -> None:
    proposal = _proposal()
    authorization = _authorization(proposal)
    assert verify_authorization(proposal, authorization, {"owner-key-2026-01": b"owner"}, _verify)


def test_changed_source_sha_is_rejected() -> None:
    proposal = _proposal()
    authorization = _authorization(proposal)
    authorization["source_sha"] = "different"
    assert not verify_authorization(proposal, authorization, {"owner-key-2026-01": b"owner"}, _verify)


def test_changed_target_branch_is_rejected() -> None:
    proposal = _proposal()
    authorization = _authorization(proposal)
    authorization["target_branch"] = "Collaboration"
    assert not verify_authorization(proposal, authorization, {"owner-key-2026-01": b"owner"}, _verify)


def test_unknown_key_and_agent_self_approval_are_rejected() -> None:
    proposal = _proposal()
    authorization = _authorization(proposal)
    assert not verify_authorization(proposal, authorization, {}, _verify)
    authorization["approved_by"] = "GPT/Codex"
    assert not verify_authorization(
        proposal, authorization, {"owner-key-2026-01": b"owner"}, _verify, producing_agent_id="GPT/Codex"
    )


def test_signature_cannot_be_replayed_on_another_proposal() -> None:
    proposal = _proposal()
    authorization = _authorization(proposal)
    other = {**proposal, "source_sha": "other-sha"}
    assert not verify_authorization(other, authorization, {"owner-key-2026-01": b"owner"}, _verify)


def test_history_rejects_duplicate_or_conflicting_events() -> None:
    proposal = _proposal()
    authorization = _authorization(proposal)
    assert validate_authorization_history([authorization])
    assert not validate_authorization_history([authorization, authorization])
    conflicting = {**authorization, "timestamp": "2026-09-02T12:01:00Z"}
    assert not validate_authorization_history([authorization, conflicting])
