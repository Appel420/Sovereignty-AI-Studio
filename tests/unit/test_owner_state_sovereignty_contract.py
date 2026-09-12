from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs" / "OWNER_STATE_SOVEREIGNTY_CONTRACT_v1.0.md"


def test_owner_state_contract_exists():
    assert CONTRACT.is_file()


def test_owner_state_contract_freezes_core_invariants():
    text = CONTRACT.read_text(encoding="utf-8")
    required = (
        "Owner is never an outsider",
        "Stateful on device, stateless when leaving",
        "Work is never held hostage",
        "Reasoning continuity is durable and owner-controlled",
        "Council operates inside the owner state boundary",
        "Transparency is mandatory",
        "Execution, state, and retention are independent authorization domains",
        "Every authorized state transition is evidence-bearing",
    )
    for phrase in required:
        assert phrase in text


def test_external_persistence_is_not_default():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "EXTERNAL_PERSISTENT" in text
    assert "Blocked by default" in text
    assert "EXTERNAL_EPHEMERAL" in text


def test_owner_access_and_action_authorization_are_separate():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "OWNER ACCESS != ACTION AUTHORIZATION" in text
    assert "EXECUTION != OWNERSHIP" in text
    assert "ASSISTANT != AUTHORITY" in text


def test_hallucination_review_alert_is_owner_visible():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "🚨 OWNER ALERT" in text
    assert "STATUS: REVIEW REQUIRED" in text
    assert "DATA EXPORTED: NONE" in text


def test_work_continuity_preserves_state_when_external_route_fails():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "EXTERNAL FAILURE" in text
    assert "CONTINUE" in text
    assert "PRESERVE TASK STATE" in text
    assert "INFORM OWNER / RESUME LATER" in text
