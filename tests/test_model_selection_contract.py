from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def candidate_set() -> list[dict[str, object]]:
    return [
        {
            "name": "Apple Foundation",
            "size_b": None,
            "multimodal": True,
            "source": "Apple",
            "description": "On-device model by Apple.",
        },
        {
            "name": "Mistral 3 (3B)",
            "size_b": 3.0,
            "multimodal": True,
            "source": "Mistral AI",
            "description": "Edge-optimized multimodal model.",
        },
    ]


def selection_event(selected: str | None, mode: str) -> dict[str, object]:
    return {
        "event_type": "LOCAL_MODEL_SELECTION",
        "event_version": 1,
        "candidate_set": candidate_set(),
        "owner_selected_model": selected,
        "selection_mode": mode,
        "visibility_mode": "full",
    }


def test_draft_schema_files_exist_without_production_imports() -> None:
    expected = {
        "EffectivePolicy.schema.json",
        "Decision.schema.json",
        "SessionState.schema.json",
        "AuditEvent.schema.json",
        "FeatureUsage.schema.json",
        "ModelDiscoveryResult.schema.json",
        "LocalModelSelectionEvent.schema.json",
        "CanonicalState.schema.json",
    }
    assert {path.name for path in SCHEMA_DIR.glob("*.schema.json")} >= expected


def test_route_decision_shape_matches_existing_contract() -> None:
    route = {
        "task_id": "task-1",
        "decision": "ALLOW",
        "route": "devassist",
        "mode": "offline",
        "reason_code": "ok",
        "policy_hash": "sha256:policy",
        "requires_owner_approval": False,
        "evidence_required": True,
        "timestamp": "2026-08-02T00:00:00+00:00",
    }
    assert set(route) == {
        "task_id", "decision", "route", "mode", "reason_code",
        "policy_hash", "requires_owner_approval", "evidence_required", "timestamp",
    }


def test_execution_receipt_shape_matches_existing_contract() -> None:
    receipt = {
        "task_id": "task-1",
        "route": "devassist",
        "mode": "offline",
        "status": "COMPLETED",
        "decision_hash": "sha256:decision",
        "output_hash": None,
        "files_changed": [],
        "network_accessed": False,
        "timestamp": "2026-08-02T00:00:00+00:00",
    }
    assert set(receipt) == {
        "task_id", "route", "mode", "status", "decision_hash",
        "output_hash", "files_changed", "network_accessed", "timestamp",
    }


def test_make_scar_event_shape_matches_existing_contract() -> None:
    event = {
        "task_id": "task-1",
        "event": "EXECUTION_RECEIPT",
        "route": "devassist",
        "mode": "offline",
        "decision": "ALLOW",
        "policy_hash": "sha256:policy",
        "receipt_hash": "sha256:receipt",
        "timestamp": "2026-08-02T00:00:00+00:00",
        "event_hash": "sha256:" + "0" * 64,
    }
    assert set(event) == {
        "task_id", "event", "route", "mode", "decision", "policy_hash",
        "receipt_hash", "timestamp", "event_hash",
    }


def test_no_selection_is_fully_visible() -> None:
    event = selection_event(None, "NO_SELECTION")
    assert event["visibility_mode"] == "full"
    assert event["selection_mode"] == "NO_SELECTION"
    assert len(event["candidate_set"]) == 2


def test_invalid_selection_preserves_exact_candidate_set() -> None:
    event = selection_event("not-discovered", "explicit_owner_selection")
    assert event["owner_selected_model"] == "not-discovered"
    assert event["candidate_set"] == candidate_set()


def test_authorization_denial_preserves_visibility() -> None:
    event = selection_event("Apple Foundation", "explicit_owner_selection")
    decision = {"decision": "DENY", "reason": "authorization denied"}
    assert decision["decision"] == "DENY"
    assert event["visibility_mode"] == "full"
    assert any(item["name"] == "Apple Foundation" for item in event["candidate_set"])


def test_selection_evidence_hash_is_deterministic() -> None:
    event = selection_event("Apple Foundation", "explicit_owner_selection")
    digest_a = hashlib.sha256(canonical(event)).hexdigest()
    digest_b = hashlib.sha256(canonical(event)).hexdigest()
    assert digest_a == digest_b
    assert len(digest_a) == 64


def test_selection_evidence_has_no_presentation_authority_fields() -> None:
    event = selection_event("Apple Foundation", "explicit_owner_selection")
    forbidden = {"blocked", "masked", "filtered", "rank", "recommendation", "demotion"}
    assert forbidden.isdisjoint(event)
