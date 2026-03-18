"""Judge Agent — resource locking and task approval.

The Judge acts as a gatekeeper: every agent must call ``approve_task`` before
executing a task that could conflict with another agent's work.  Exclusive
resource locks prevent overlapping execution and are recorded for audit
purposes.

Usage::

    judge = JudgeAgent()
    judge.start_metrics()

    approved, reason = await judge.approve_task("ai_router", {"resource": "openai"})
    if approved:
        # … do work …
        await judge.release_task("ai_router", "openai")
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple

from agents.judge_agent import metrics as _metrics

logger = logging.getLogger(__name__)


class JudgeAgent:
    """Thread-safe resource lock manager with Prometheus instrumentation."""

    def __init__(self) -> None:
        # resource_key -> {"agent_id": str, "acquired_at": float}
        self._locks: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._task_log: list = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_metrics(self) -> None:
        """Start the Prometheus metrics HTTP server."""
        _metrics.start_metrics_server()

    async def approve_task(
        self,
        agent_id: str,
        task: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Check whether *agent_id* may execute *task*.

        A task is approved when the resource it requests is not currently held
        by another agent.  The resource key is taken from
        ``task.get("resource", agent_id)``.

        Returns:
            A ``(approved: bool, reason: str)`` tuple.
        """
        resource = task.get("resource", agent_id)
        async with self._lock:
            holder = self._locks.get(resource)
            if holder and holder["agent_id"] != agent_id:
                reason = (
                    f"Resource '{resource}' locked by '{holder['agent_id']}' "
                    f"since {holder['acquired_at']:.1f}"
                )
                self._log_event(agent_id, task, approved=False, reason=reason)
                _metrics.inc_rejected(agent_id)
                logger.warning(
                    "Judge REJECTED %s for '%s': %s", agent_id, resource, reason
                )
                return False, reason

            self._locks[resource] = {
                "agent_id": agent_id,
                "acquired_at": time.monotonic(),
            }
            reason = f"Resource '{resource}' granted to '{agent_id}'"
            self._log_event(agent_id, task, approved=True, reason=reason)
            _metrics.inc_approved(agent_id)
            logger.info("Judge APPROVED %s for '%s'", agent_id, resource)
            return True, reason

    async def release_task(
        self,
        agent_id: str,
        resource: Optional[str] = None,
    ) -> None:
        """Release the lock held by *agent_id* on *resource*.

        If *resource* is ``None`` the lock key defaults to *agent_id*.
        """
        resource_key = resource or agent_id
        async with self._lock:
            holder = self._locks.get(resource_key)
            if holder and holder["agent_id"] == agent_id:
                del self._locks[resource_key]
                _metrics.inc_released(agent_id)
                logger.info(
                    "Judge RELEASED '%s' by '%s'", resource_key, agent_id
                )
            else:
                logger.warning(
                    "Judge: '%s' tried to release '%s' but doesn't hold it",
                    agent_id,
                    resource_key,
                )

    def get_task_log(self) -> list:
        """Return a copy of the internal task event log."""
        return list(self._task_log)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _log_event(
        self,
        agent_id: str,
        task: Dict[str, Any],
        approved: bool,
        reason: str,
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "agent_id": agent_id,
            "task": task,
            "approved": approved,
            "reason": reason,
        }
        self._task_log.append(entry)
        # Keep log bounded
        if len(self._task_log) > 10_000:
            self._task_log = self._task_log[-5_000:]
