"""I-008 deterministic transparency enforcement.

This module is the fail-closed execution boundary. Every side-effecting caller
must provide a declaration, a schema-valid option set and selected option, a
pre-action evidence sink, and an explicit owner decision before execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence, TypeVar

from jsonschema import Draft202012Validator

DECISION_CLASSES = frozenset({"ALLOW", "DENY", "REQUIRE_APPROVAL"})
OWNER_DECISIONS = frozenset({"ALLOW", "DENY"})
OwnerSink = Callable[[Mapping[str, Any]], None]
T = TypeVar("T")


class I008Violation(ValueError):
    """Raised whenever an I-008 hard gate is violated."""


@dataclass(frozen=True, slots=True)
class ActionDeclaration:
    action_id: str
    decision_class: str
    owner_id: str
    capability_id: str
    policy_hash: str
    side_effects: tuple[str, ...]
    data_egress: tuple[str, ...]
    persistence: tuple[str, ...]
    provider_or_technology: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "decision_class": self.decision_class,
            "owner_id": self.owner_id,
            "capability_id": self.capability_id,
            "policy_hash": self.policy_hash,
            "side_effects": list(self.side_effects),
            "data_egress": list(self.data_egress),
            "persistence": list(self.persistence),
            "provider_or_technology": list(self.provider_or_technology),
        }


def _required_nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise I008Violation(f"I-008: {field} is required")
    return value.strip()


def _nonempty_strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise I008Violation(f"I-008: {field} must be a sequence of strings")
    result = tuple(value)
    if not result or any(not isinstance(item, str) or not item.strip() for item in result):
        raise I008Violation(f"I-008: {field} must contain at least one non-empty entry")
    return result


def validate_option_set(option_set: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(option_set), key=lambda e: list(e.path))
    if errors:
        path = ".".join(map(str, errors[0].path)) or "$"
        raise I008Violation(f"I-008 option-set invalid at {path}: {errors[0].message}")


def select_option(option_set: Mapping[str, Any], selected_option_id: str) -> Mapping[str, Any]:
    selected_option_id = _required_nonempty(selected_option_id, "selected_option_id")
    options = option_set.get("options")
    if not isinstance(options, Sequence):
        raise I008Violation("I-008: option set has no selectable options")
    for option in options:
        if isinstance(option, Mapping) and option.get("id") == selected_option_id:
            return option
    raise I008Violation(f"I-008: selected option is not present in the option set: {selected_option_id!r}")


def declare_action(*, action_id: str, decision_class: str, owner_id: str, capability_id: str, policy_hash: str, side_effects: Sequence[str], data_egress: Sequence[str], persistence: Sequence[str], provider_or_technology: Sequence[str]) -> ActionDeclaration:
    if decision_class not in DECISION_CLASSES:
        raise I008Violation(f"I-008: invalid decision class: {decision_class!r}")
    return ActionDeclaration(
        action_id=_required_nonempty(action_id, "action_id"),
        decision_class=decision_class,
        owner_id=_required_nonempty(owner_id, "owner_id"),
        capability_id=_required_nonempty(capability_id, "capability_id"),
        policy_hash=_required_nonempty(policy_hash, "policy_hash"),
        side_effects=_nonempty_strings(side_effects, "side_effects"),
        data_egress=_nonempty_strings(data_egress, "data_egress"),
        persistence=_nonempty_strings(persistence, "persistence"),
        provider_or_technology=_nonempty_strings(provider_or_technology, "provider_or_technology"),
    )


def _incident(message: str, *, incident: OwnerSink, owner_alert: OwnerSink, context: Mapping[str, Any]) -> None:
    payload = {"invariant": "I-008", "event": "incident", "violation": message, **context}
    incident(payload)
    owner_alert(payload)
    raise I008Violation(message)


def authorize_action(*, declaration: ActionDeclaration | None, option_set: Mapping[str, Any] | None, selected_option_id: str | None, option_schema: Mapping[str, Any], owner_decision: str, pre_action_evidence: OwnerSink, incident: OwnerSink, owner_alert: OwnerSink) -> Mapping[str, Any]:
    context = {"owner_decision": owner_decision}
    if declaration is None:
        _incident("I-008: action declaration is required before execution", incident=incident, owner_alert=owner_alert, context=context)
    if option_set is None:
        _incident("I-008: valid option set is required before selection", incident=incident, owner_alert=owner_alert, context=context)
    try:
        validate_option_set(option_set, option_schema)
        selected = select_option(option_set, selected_option_id or "")
    except I008Violation as exc:
        _incident(str(exc), incident=incident, owner_alert=owner_alert, context=context)
    if owner_decision not in OWNER_DECISIONS:
        _incident("I-008: owner decision must be explicit ALLOW or DENY", incident=incident, owner_alert=owner_alert, context=context)
    event = {
        "invariant": "I-008",
        "event": "pre_action_declaration",
        "declaration": declaration.as_dict(),
        "option_set": dict(option_set),
        "selected_option": dict(selected),
        "selected_option_id": selected_option_id,
        "owner_decision": owner_decision,
    }
    try:
        pre_action_evidence(event)
    except Exception as exc:
        _incident("I-008: pre-action SCAR evidence could not be recorded", incident=incident, owner_alert=owner_alert, context={**context, "error_type": type(exc).__name__})
    if owner_decision == "DENY":
        return {**event, "execution": "BLOCKED"}
    if declaration.decision_class != "ALLOW":
        _incident("I-008: declaration does not authorize execution", incident=incident, owner_alert=owner_alert, context=context)
    return event


def execute_authorized_action(*, declaration: ActionDeclaration | None, option_set: Mapping[str, Any] | None, selected_option_id: str | None, option_schema: Mapping[str, Any], owner_decision: str, pre_action_evidence: OwnerSink, incident: OwnerSink, owner_alert: OwnerSink, action: Callable[[], T], post_action_receipt: OwnerSink) -> T | None:
    event = authorize_action(
        declaration=declaration,
        option_set=option_set,
        selected_option_id=selected_option_id,
        option_schema=option_schema,
        owner_decision=owner_decision,
        pre_action_evidence=pre_action_evidence,
        incident=incident,
        owner_alert=owner_alert,
    )
    if event["execution"] == "BLOCKED":
        return None
    result: T | None = None
    action_error: BaseException | None = None
    try:
        result = action()
    except BaseException as exc:
        action_error = exc
    receipt = {
        "invariant": "I-008",
        "event": "post_action_receipt",
        "status": "FAILED" if action_error else "COMPLETED",
        "action_id": declaration.action_id,
        "capability_id": declaration.capability_id,
        "policy_hash": declaration.policy_hash,
        "result_type": type(result).__name__ if action_error is None else None,
        "error_type": type(action_error).__name__ if action_error else None,
    }
    try:
        post_action_receipt(receipt)
    except Exception as exc:
        _incident("I-008: post-action receipt could not be recorded", incident=incident, owner_alert=owner_alert, context={"error_type": type(exc).__name__})
    if action_error is not None:
        raise action_error
    return result
