"""I-008 deterministic transparency enforcement.

This module is deliberately fail-closed. Schema validation alone cannot enforce
ordering, so execution must enter through ``authorize_action`` only after the
pre-action declaration has been validated and recorded by the supplied evidence
sink.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from jsonschema import Draft202012Validator


DECISION_CLASSES = frozenset({"ALLOW", "DENY", "REQUIRE_APPROVAL"})


class I008Violation(ValueError):
    """Raised whenever a required I-008 pre-action condition is absent."""


@dataclass(frozen=True)
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


def declare_action(
    *,
    decision_class: str,
    side_effects: Sequence[str],
    data_egress: Sequence[str],
    persistence: Sequence[str],
    provider_or_technology: Sequence[str],
) -> ActionDeclaration:
    """Construct a complete, auditable pre-action declaration."""
    if decision_class not in DECISION_CLASSES:
        raise I008Violation(f"I-008: invalid decision class: {decision_class!r}")
    return ActionDeclaration(
        decision_class=decision_class,
        side_effects=_nonempty_strings(side_effects, "side_effects"),
        data_egress=_nonempty_strings(data_egress, "data_egress"),
        persistence=_nonempty_strings(persistence, "persistence"),
        provider_or_technology=_nonempty_strings(provider_or_technology, "provider_or_technology"),
    )


def authorize_action(
    *,
    declaration: ActionDeclaration | None,
    owner_decision: str,
    pre_action_evidence: Callable[[Mapping[str, Any]], None],
) -> None:
    """Fail closed unless I-008 preconditions have been satisfied.

    ``pre_action_evidence`` MUST durably record the declaration before this
    function returns. The action itself must execute only after this function.
    """
    if declaration is None:
        raise I008Violation("I-008: action declaration is required before execution")
    if owner_decision not in {"ALLOW", "DENY"}:
        raise I008Violation("I-008: owner decision must be ALLOW or DENY")

    event = {
        "invariant": "I-008",
        "event": "pre_action_declaration",
        "declaration": declaration.as_dict(),
        "owner_decision": owner_decision,
    }
    try:
        pre_action_evidence(event)
    except Exception as exc:  # evidence failure must prevent execution
        raise I008Violation("I-008: pre-action evidence could not be recorded") from exc

    if owner_decision != "ALLOW":
        raise I008Violation("I-008: action denied; execution is prohibited")
    if declaration.decision_class != "ALLOW":
        raise I008Violation("I-008: declaration does not authorize execution")
