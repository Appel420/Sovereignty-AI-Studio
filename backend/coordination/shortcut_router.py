"""Translate device Shortcut Flow input into governed coordination contracts.

This module parses and classifies input, asks an injected authority function for
permission, and delegates route selection to Genesis. It does not call models,
execute tools, or write SCAR/REPMHL evidence.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .execution_contracts import HumanEscalationEvent, RouteDecision
from .genesis_adapter import GenesisRouterAdapter
from .task_envelope import TaskEnvelope


GateAuthorize = Callable[[TaskEnvelope, Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ShortcutRoutingResult:
    """Non-executing result of Shortcut Flow parsing and Gate authorization."""

    task: TaskEnvelope
    task_type: str
    authorization: Mapping[str, Any]
    route: RouteDecision | None
    escalation: HumanEscalationEvent | None = None


class ShortcutRouter:
    """Convert a Shortcut Flow document into a governed route decision."""

    def __init__(
        self,
        gate_authorize: GateAuthorize,
        *,
        genesis: GenesisRouterAdapter | None = None,
    ) -> None:
        if not callable(gate_authorize):
            raise TypeError("gate_authorize must be callable")
        self._gate_authorize = gate_authorize
        self._genesis = genesis or GenesisRouterAdapter()

    def route(self, document: Mapping[str, Any]) -> ShortcutRoutingResult:
        if not isinstance(document, Mapping):
            raise TypeError("Shortcut Flow document must be a mapping")

        request = _request(document)
        request_id = _required_string(request, "request_id")
        prompt = str(request.get("prompt", ""))
        permissions = _mapping(request.get("permissions"))
        routing = _mapping(request.get("routing_decision"))
        task_type = classify_prompt(prompt, routing)
        mode = _mode_for(permissions, task_type)
        scope = _scope_for(task_type, permissions)

        task = TaskEnvelope(
            task_id=request_id,
            requester="user",
            owner="owner",
            requested_agent="devassist420" if task_type == "CODING" else None,
            scope=scope,
            mode=mode,
            requires_owner_approval=bool(routing.get("judge_required", False)),
        )
        authorization = self._gate_authorize(task, _authorization_request(request, task_type))
        if not isinstance(authorization, Mapping):
            raise TypeError("Gate authorization must return a mapping")

        decision = str(authorization.get("decision", "")).upper()
        if decision not in {"ALLOW", "APPROVED", "OWNER_AUTHORIZED", "DELEGATED_AUTHORIZED", "OWNER_OVERRIDE"}:
            escalation = HumanEscalationEvent(
                task_id=task.task_id,
                reason_code=str(authorization.get("reason_code", "AUTHORIZATION_REQUIRED")),
                requested_scope=task.scope,
                policy_hash=str(authorization.get("policy_hash", "")),
            )
            return ShortcutRoutingResult(task, task_type, authorization, None, escalation)

        route = self._genesis.decide(task, authorization)
        return ShortcutRoutingResult(task, task_type, authorization, route)


def classify_prompt(prompt: str, routing: Mapping[str, Any] | None = None) -> str:
    """Apply the Shortcut Flow classifier precedence without executing anything."""
    text = prompt.lower()
    hints = routing or {}
    if hints.get("task_type"):
        return str(hints["task_type"]).upper()
    if any(token in text for token in ("repository", "code", "coding", "pull request", "commit")):
        return "CODING"
    if any(token in text for token in ("summarize", "summarise", "analyze document", "analyse document")):
        return "SYNTHESIS"
    if any(token in text for token in ("story", "creative", "write", "draft")):
        return "WRITING"
    if any(token in text for token in ("security", "privacy", "legal", "medical")):
        return "HIGH_RISK"
    if any(token in text for token in ("voice", "audio", "narrate")):
        return "AUDIO"
    if any(token in text for token in ("on device", "on-device", "local execution")):
        return "ON_DEVICE"
    return "UNKNOWN"


def _request(document: Mapping[str, Any]) -> Mapping[str, Any]:
    request = document.get("request")
    return request if isinstance(request, Mapping) else document


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _required_string(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key} is required")
    return result


def _mode_for(permissions: Mapping[str, Any], task_type: str) -> str:
    if task_type == "ON_DEVICE" or not permissions.get("external_models", False):
        return "offline"
    return "online"


def _scope_for(task_type: str, permissions: Mapping[str, Any]) -> tuple[str, ...]:
    scope: list[str] = [f"task:{task_type.lower()}"]
    if permissions.get("device_access") is True:
        scope.append("device")
    if permissions.get("memory_access") is True:
        scope.append("memory")
    if permissions.get("external_models") is True:
        scope.append("external-models")
    return tuple(scope)


def _authorization_request(request: Mapping[str, Any], task_type: str) -> dict[str, Any]:
    permissions = _mapping(request.get("permissions"))
    return {
        "request_id": request.get("request_id"),
        "task_type": task_type,
        "permissions": dict(permissions),
        "memory_allowed": bool(permissions.get("memory_access", False)),
        "device_allowed": bool(permissions.get("device_access", False)),
        "external_models_allowed": bool(permissions.get("external_models", False)),
    }
