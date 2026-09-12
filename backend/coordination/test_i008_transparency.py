"""Executable I-008 gate tests: prove ordering and fail-closed behavior."""
from __future__ import annotations

import pytest

from backend.coordination.i008_transparency import (
    I008Violation,
    authorize_action,
    declare_action,
    execute_authorized_action,
)

SCHEMA = {
    "type": "object",
    "required": ["options"],
    "properties": {
        "options": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["id", "label", "pros", "cons", "risks", "rewards"],
            "properties": {
                "id": {"type": "string", "minLength": 1}, "label": {"type": "string", "minLength": 1},
                "pros": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
                "cons": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
                "risks": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
                "rewards": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
            }, "additionalProperties": True,
        }}
    }, "additionalProperties": True,
}


def declaration():
    return declare_action(action_id="a-1", decision_class="ALLOW", owner_id="Appel420", capability_id="cap-1", policy_hash="sha256:p", side_effects=["write file"], data_egress=["none"], persistence=["local file"], provider_or_technology=["local filesystem"])


def options():
    return {"options": [{"id": "safe", "label": "Safe", "pros": ["works"], "cons": ["takes time"], "risks": ["bounded"], "rewards": ["verified"]}]}


def sinks():
    events = []
    incidents = []
    alerts = []
    return events, incidents, alerts


def test_missing_declaration_blocks_before_action():
    events, incidents, alerts = sinks(); ran = []
    with pytest.raises(I008Violation):
        execute_authorized_action(declaration=None, option_set=options(), selected_option_id="safe", option_schema=SCHEMA, owner_decision="ALLOW", pre_action_evidence=events.append, incident=incidents.append, owner_alert=alerts.append, action=lambda: ran.append(1), post_action_receipt=events.append)
    assert ran == [] and incidents and alerts


def test_invalid_option_blocks_before_action():
    events, incidents, alerts = sinks(); ran = []
    with pytest.raises(I008Violation):
        execute_authorized_action(declaration=declaration(), option_set={"options": [{"id": "bad", "label": "Bad", "pros": [], "cons": ["x"], "risks": ["x"], "rewards": ["x"]}]}, selected_option_id="bad", option_schema=SCHEMA, owner_decision="ALLOW", pre_action_evidence=events.append, incident=incidents.append, owner_alert=alerts.append, action=lambda: ran.append(1), post_action_receipt=events.append)
    assert ran == []


def test_missing_pre_action_evidence_blocks():
    events, incidents, alerts = sinks(); ran = []
    def fail(_): raise RuntimeError("audit down")
    with pytest.raises(I008Violation):
        execute_authorized_action(declaration=declaration(), option_set=options(), selected_option_id="safe", option_schema=SCHEMA, owner_decision="ALLOW", pre_action_evidence=fail, incident=incidents.append, owner_alert=alerts.append, action=lambda: ran.append(1), post_action_receipt=events.append)
    assert ran == [] and incidents and alerts


def test_deny_is_no_action_not_incident():
    events, incidents, alerts = sinks(); ran = []
    assert execute_authorized_action(declaration=declaration(), option_set=options(), selected_option_id="safe", option_schema=SCHEMA, owner_decision="DENY", pre_action_evidence=events.append, incident=incidents.append, owner_alert=alerts.append, action=lambda: ran.append(1), post_action_receipt=events.append) is None
    assert ran == [] and not incidents and not alerts


def test_allow_executes_only_after_pre_action_event_and_receipt():
    events, incidents, alerts = sinks(); order = []
    def evidence(event): order.append(event["event"])
    def action(): order.append("action"); return "ok"
    def receipt(event): order.append(event["event"])
    assert execute_authorized_action(declaration=declaration(), option_set=options(), selected_option_id="safe", option_schema=SCHEMA, owner_decision="ALLOW", pre_action_evidence=evidence, incident=incidents.append, owner_alert=alerts.append, action=action, post_action_receipt=receipt) == "ok"
    assert order == ["pre_action_declaration", "action", "post_action_receipt"]


def test_action_failure_still_gets_receipt():
    events, incidents, alerts = sinks(); receipts = []
    def action(): raise RuntimeError("boom")
    with pytest.raises(RuntimeError, match="boom"):
        execute_authorized_action(declaration=declaration(), option_set=options(), selected_option_id="safe", option_schema=SCHEMA, owner_decision="ALLOW", pre_action_evidence=events.append, incident=incidents.append, owner_alert=alerts.append, action=action, post_action_receipt=receipts.append)
    assert receipts[0]["status"] == "FAILED"
