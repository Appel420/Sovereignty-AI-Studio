import json
from pathlib import Path

import pytest

from backend.coordination.i008_transparency import (
    I008Violation,
    authorize_action,
    declare_action,
    execute_authorized_action,
    validate_option_set,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/option-set-with-risk-reward.schema.json").read_text())


def valid_options():
    return {"options": [{
        "id": "deploy",
        "label": "Deploy",
        "pros": ["Release the verified build"],
        "cons": ["Changes production state"],
        "risks": ["Deployment failure"],
        "rewards": ["New version becomes available"],
    }]}


def declaration(decision="ALLOW"):
    return declare_action(
        decision_class=decision,
        side_effects=["deployment"],
        data_egress=["none"],
        persistence=["deployment state"],
        provider_or_technology=["local runner"],
    )


def sinks():
    events = []
    return events, events.append, events.append, events.append, events.append


def test_option_set_contract_accepts_complete_option():
    validate_option_set(valid_options(), SCHEMA)


def test_option_set_contract_rejects_missing_risk_reward_fields():
    option = valid_options()
    del option["options"][0]["risks"]
    with pytest.raises(I008Violation):
        validate_option_set(option, SCHEMA)


def test_option_set_contract_rejects_empty_analysis():
    option = valid_options()
    option["options"][0]["risks"] = []
    with pytest.raises(I008Violation):
        validate_option_set(option, SCHEMA)


def test_declaration_requires_valid_decision_class():
    with pytest.raises(I008Violation):
        declaration("MAYBE")


def test_authorization_requires_option_set_and_records_pre_action_evidence():
    events, evidence, incident, alert, _ = sinks()
    authorize_action(
        declaration=declaration(), option_set=valid_options(), option_schema=SCHEMA,
        owner_decision="ALLOW", pre_action_evidence=evidence, incident=incident, owner_alert=alert,
    )
    assert events[0]["invariant"] == "I-008"
    assert events[0]["event"] == "pre_action_declaration"


def test_authorization_fails_closed_without_declaration():
    _, evidence, incident, alert, _ = sinks()
    with pytest.raises(I008Violation):
        authorize_action(
            declaration=None, option_set=valid_options(), option_schema=SCHEMA,
            owner_decision="ALLOW", pre_action_evidence=evidence, incident=incident, owner_alert=alert,
        )


def test_authorization_fails_closed_without_option_set():
    _, evidence, incident, alert, _ = sinks()
    with pytest.raises(I008Violation):
        authorize_action(
            declaration=declaration(), option_set=None, option_schema=SCHEMA,
            owner_decision="ALLOW", pre_action_evidence=evidence, incident=incident, owner_alert=alert,
        )


def test_authorization_fails_closed_when_evidence_write_fails():
    _, _, incident, alert, _ = sinks()
    def fail(_):
        raise RuntimeError("ledger unavailable")
    with pytest.raises(I008Violation):
        authorize_action(
            declaration=declaration(), option_set=valid_options(), option_schema=SCHEMA,
            owner_decision="ALLOW", pre_action_evidence=fail, incident=incident, owner_alert=alert,
        )


def test_deny_never_executes():
    _, evidence, incident, alert, _ = sinks()
    executed = []
    with pytest.raises(I008Violation):
        execute_authorized_action(
            declaration=declaration("DENY"), option_set=valid_options(), option_schema=SCHEMA,
            owner_decision="DENY", pre_action_evidence=evidence, incident=incident, owner_alert=alert,
            action=lambda: executed.append(True), post_action_receipt=evidence,
        )
    assert executed == []


def test_action_and_receipt_are_ordered_after_allow():
    events = []
    def record(event):
        events.append(event)
    result = execute_authorized_action(
        declaration=declaration(), option_set=valid_options(), option_schema=SCHEMA,
        owner_decision="ALLOW", pre_action_evidence=record, incident=record, owner_alert=record,
        action=lambda: "done", post_action_receipt=record,
    )
    assert result == "done"
    assert [event["event"] for event in events] == ["pre_action_declaration", "post_action_receipt"]
