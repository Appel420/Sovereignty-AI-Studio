"""I-008 deterministic transparency enforcement.

Fail-closed execution boundary. Schema validation is structural only; this
module enforces declaration, option-set, pre-action evidence, explicit owner
ALLOW, action execution, and post-action receipt sequencing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence, TypeVar

from jsonschema import Draft202012Validator

DECISION_CLASSES = frozenset({"ALLOW", "DENY", "REQUIRE_APPROVAL"})
OwnerSink = Callable[[Mapping[str, Any]], None]
T = TypeVar("T")


class I008Violation(ValueError):
    """Raised whenever an I-008 hard gate is violated."""


@dataclass(frozen=True, slots=True)
class ActionDeclaration:
    decision_class: str
    side_effects: tuple[str, ...]
    data_egress: tuple[str, ...]
    persistence: tuple[str, ...]
    provider_or_technology: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_class": self.decision_class,
            "side_effects": list(self.side_effects),
            "data_egress": list(self.data_egress),
            "persistence": list(self.persistence),
            "provider_or_technology": list(self.provider_or_technology),
        }


def _nonempty_strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise I008Violation(f"I-008: {field} must be a sequence of strings")
    result = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise I008Violation(f"I-008: {field} contains an invalid entry")
    return result


def validate_option_set(option_set: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    """Validate the frozen OptionSetWithRiskReward contract."""
    errors = sorted(Draft202012Validator(schema).iter_errors(option_set), key=lambda e: list(e.path))
    if errors:
        path = ".".join(map(str, errors[0].path)) or "$"
        raise I008Violation(f"I-008 option-set invalid at {path}: {errors[0].message}")


def declare_action(*, decision_class: str, side_effects: Sequence[str], data_egress: Sequence[str], persistence: Sequence[str], provider_or_technology: Sequence[str]) -> ActionDeclaration:
    """Construct the complete pre-action declaration."""
    if decision_class not in DECISION_CLASSES:
        raise I008Violation(f"I-008: invalid decision class: {decision_class!r}")
    return ActionDeclaration(
        decision_class=decision_class,
        side_effects=_nonempty_strings(side_effects, "side_effects"),
        data_egress=_nonempty_strings(data_egress, "data_egress"),
        persistence=_nonempty_strings(persistence, "persistence"),
        provider_or_technology=_nonempty_strings(provider_or_technology, "provider_or_technology"),
    )


def _reject(message: str, *, incident: OwnerSink, owner_alert: OwnerSink, context: Mapping[str, Any]) -> None:
    """Record the deterministic I-008 failure path before raising."""
    payload = {"invariant": "I-008", "event": "incident", "violation": message, **context}
    incident(payload)
    owner_alert(payload)
    raise I008Violation(message)


def authorize_action(*, declaration: ActionDeclaration | None, option_set: Mapping[str, Any] | None, option_schema: Mapping[str, Any], owner_decision: str, pre_action_evidence: OwnerSink, incident: OwnerSink, owner_alert: OwnerSink) -> None:
    """Enforce declaration -> option set -> pre-action evidence -> ALLOW."""
    context = {"owner_decision": owner_decision}
    if declaration is None:
        _reject("I-008: action declaration is required before execution", incident=incident, owner_alert=owner_alert, context=context)
    if option_set is None:
        _reject("I-008: valid option set is required before selection", incident=incident, owner_alert=owner_alert, context=context)
    try:
        validate_option_set(option_set, option_schema)
    except I008Violation as exc:
        _reject(str(exc), incident=incident, owner_alert=owner_alert, context=context)
    if owner_decision not in {"ALLOW", "DENY"}:
        _reject("I-008: owner decision must be explicit ALLOW or DENY", incident=incident, owner_alert=owner_alert, context=context)
    event = {
        "invariant": "I-008",
        "event": "pre_action_declaration",
        "declaration": declaration.as_dict(),
        "option_set": dict(option_set),
        "owner_decision": owner_decision,
    }
    try:
        pre_action_evidence(event)
    except Exception as exc:
        _reject("I-008: pre-action SCAR evidence could not be recorded", incident=incident, owner_alert=owner_alert, context=context)
    if owner_decision != "ALLOW":
        _reject("I-008: action denied; execution is prohibited", incident=incident, owner_alert=owner_alert, context=context)
    if declaration.decision_class != "ALLOW":
        _reject("I-008: declaration does not authorize execution", incident=incident, owner_alert=owner_alert, context=context)


def execute_authorized_action(*, declaration: ActionDeclaration | None, option_set: Mapping[str, Any] | None, option_schema: Mapping[str, Any], owner_decision: str, pre_action_evidence: OwnerSink, incident: OwnerSink, owner_alert: OwnerSink, action: Callable[[], T], post_action_receipt: OwnerSink) -> T:
    """Only supported I-008 action entry point; emits mandatory receipt."""
    authorize_action(
        declaration=declaration,
        option_set=option_set,
        option_schema=option_schema,
        owner_decision=owner_decision,
        pre_action_evidence=pre_action_evidence,
        incident=incident,
        owner_alert=owner_alert,
    )
    result = action()
    receipt = {"invariant": "I-008", "event": "post_action_receipt", "status": "COMPLETED", "result_type": type(result).__name__}
    try:
        post_action_receipt(receipt)
    except Exception as exc:
        incident({"invariant": "I-008", "event": "incident", "violation": "post-action receipt could not be recorded"})
        owner_alert({"invariant": "I-008", "event": "incident", "violation": "post-action receipt could not be recorded"})
        raise I008Violation("I-008: post-action receipt could not be recorded") from exc
    return result
