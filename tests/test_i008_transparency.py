import json
from pathlib import Path

import pytest

from backend.coordination.i008_transparency import (
    I008Violation,
    authorize_action,
    declare_action,
    validate_option_set,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/option-set-with-risk-reward.schema.json").read_text())


def valid_options():
    return {
        "options": [{
            "id": "deploy",
            "label": "Deploy",
            "pros": ["Release the verified build"],
            "cons": ["Changes production state"],
            "risks": ["Deployment failure"],
            "rewards": ["New version becomes available"],
        }]
    }


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
        declare_action(
            decision_class="MAYBE",
            side_effects=["state change"],
            data_egress=["none"],
            persistence=["none"],
            provider_or_technology=["local"],
        )


def test_authorization_records_evidence_before_allow_returns():
    events = []
    declaration = declare_action(
        decision_class="ALLOW",
        side_effects=["deployment"],
        data_egress=["none"],
        persistence=["deployment state"],
        provider_or_technology=["local runner"],
    )
    authorize_action(declaration=declaration, owner_decision="ALLOW", pre_action_evidence=events.append)
    assert events and events[0]["invariant"] == "I-008"
    assert events[0]["event"] == "pre_action_declaration"


def test_authorization_fails_closed_without_declaration():
    with pytest.raises(I008Violation):
        authorize_action(declaration=None, owner_decision="ALLOW", pre_action_evidence=lambda _: None)


def test_authorization_fails_closed_when_evidence_write_fails():
    declaration = declare_action(
        decision_class="ALLOW",
        side_effects=["state change"],
        data_egress=["none"],
        persistence=["state"],
        provider_or_technology=["local"],
    )
    with pytest.raises(I008Violation):
        authorize_action(
            declaration=declaration,
            owner_decision="ALLOW",
            pre_action_evidence=lambda _: (_ for _ in ()).throw(RuntimeError("ledger unavailable")),
        )


def test_deny_never_returns_authorized():
    declaration = declare_action(
        decision_class="DENY",
        side_effects=["none"],
        data_egress=["none"],
        persistence=["audit event"],
        provider_or_technology=["local"],
    )
    with pytest.raises(I008Violation):
        authorize_action(declaration=declaration, owner_decision="DENY", pre_action_evidence=lambda _: None)
