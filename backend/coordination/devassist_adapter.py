"""DevAssist local execution boundary.

The adapter accepts an already-authorized route and an injected local executor.
It does not authorize, expand scope, contact providers, or create policy.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .execution_contracts import ExecutionReceipt, RouteDecision
from .task_envelope import TaskEnvelope


LocalExecutor = Callable[[TaskEnvelope, RouteDecision], Mapping[str, Any]]


class DevAssistExecutionAdapter:
    """Execute only through an explicitly injected local operation."""

    def __init__(self, executor: LocalExecutor, *, allowed_routes: set[str] | None = None) -> None:
        if not callable(executor):
            raise TypeError("executor must be callable")
        self._executor = executor
        self._allowed_routes = {"devassist"} if allowed_routes is None else set(allowed_routes)
        if not self._allowed_routes or any(not isinstance(route, str) or not route for route in self._allowed_routes):
            raise ValueError("allowed_routes must contain at least one non-empty route")

    def execute(self, task: TaskEnvelope, route: RouteDecision) -> ExecutionReceipt:
        if not isinstance(task, TaskEnvelope):
            raise TypeError("task must be a TaskEnvelope")
        if not isinstance(route, RouteDecision):
            raise TypeError("route must be a RouteDecision")
        if route.task_id != task.task_id:
            raise ValueError("task and route task_id do not match")
        if route.decision != "ALLOW":
            raise PermissionError("execution requires an ALLOW route decision")
        if route.mode != task.mode:
            raise ValueError("task and route modes do not match")
        if route.route not in self._allowed_routes:
            raise PermissionError(f"route is not enabled for DevAssist: {route.route}")

        result = self._executor(task, route)
        if not isinstance(result, Mapping):
            raise TypeError("local executor must return a mapping")

        files_changed = result.get("files_changed", ())
        if not isinstance(files_changed, (list, tuple)) or not all(
            isinstance(path, str) and path for path in files_changed
        ):
            raise ValueError("files_changed must be a sequence of non-empty paths")

        network_accessed = result.get("network_accessed", False)
        if not isinstance(network_accessed, bool):
            raise ValueError("network_accessed must be boolean")

        output_hash = result.get("output_hash")
        if output_hash is not None and (not isinstance(output_hash, str) or not output_hash):
            raise ValueError("output_hash must be a non-empty string when provided")

        return ExecutionReceipt(
            task_id=task.task_id,
            route=route.route,
            mode=task.mode,
            status=str(result.get("status", "COMPLETED")),
            decision_hash=_decision_hash(route),
            output_hash=output_hash,
            files_changed=tuple(files_changed),
            network_accessed=network_accessed,
        )


def _decision_hash(route: RouteDecision) -> str:
    import hashlib
    import json

    encoded = json.dumps(route.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
