"""
Judge supervisor — resource locking, task approval/rejection, conflict prevention.
Extends Judge_build.py orchestration with async coordination.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Any

from app.services.event_bus import event_bus, Event

logger = logging.getLogger(__name__)

# Task decision constants
APPROVED = "approved"
REJECTED = "rejected"
PENDING = "pending"


@dataclass
class Task:
    task_id: str
    agent_id: str
    action: str
    payload: Dict
    status: str = PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    submitted_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    decided_at: Optional[str] = None
    locked_resources: Set[str] = field(default_factory=set)


class JudgeSupervisor:
    """
    Supervises multi-agent task execution.

    Responsibilities:
    - Approve or reject tasks based on resource availability and policy
    - Maintain exclusive resource locks to prevent conflicts
    - Broadcast task lifecycle events on the event bus
    - Enforce rate limits per agent
    """

    def __init__(self, max_concurrent_tasks: int = 10):
        self._tasks: Dict[str, Task] = {}
        self._locks: Dict[str, str] = {}          # resource_key → task_id
        self._lock = asyncio.Lock()
        self._max_concurrent = max_concurrent_tasks
        self._agent_task_counts: Dict[str, int] = {}

    async def submit(
        self,
        task_id: str,
        agent_id: str,
        action: str,
        payload: Dict,
        required_resources: Optional[Set[str]] = None,
    ) -> Task:
        """
        Submit a task for judge review.
        Returns the Task object with status=approved or status=rejected.
        """
        async with self._lock:
            task = Task(
                task_id=task_id,
                agent_id=agent_id,
                action=action,
                payload=payload,
                locked_resources=required_resources or set(),
            )
            self._tasks[task_id] = task

            # Policy checks
            active_count = sum(
                1 for t in self._tasks.values() if t.status == PENDING
            )
            if active_count >= self._max_concurrent:
                return self._reject(task, "Max concurrent task limit reached")

            agent_count = self._agent_task_counts.get(agent_id, 0)
            if agent_count >= 3:
                return self._reject(task, f"Agent {agent_id} has too many pending tasks")

            # Resource conflict check
            for resource in task.locked_resources:
                if resource in self._locks:
                    holder = self._locks[resource]
                    return self._reject(
                        task, f"Resource '{resource}' locked by task {holder}"
                    )

            # All checks passed — approve
            for resource in task.locked_resources:
                self._locks[resource] = task_id
            task.status = APPROVED
            task.decided_at = datetime.now(tz=timezone.utc).isoformat()
            self._agent_task_counts[agent_id] = agent_count + 1

        await event_bus.publish(
            Event(
                topic="judge.task.approved",
                payload={"task_id": task_id, "agent_id": agent_id, "action": action},
                source="judge_supervisor",
            )
        )
        logger.info("Task %s approved for agent %s action=%s", task_id, agent_id, action)
        return task

    async def complete(
        self,
        task_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """Mark a task as completed and release its resources."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.status = "completed" if error is None else "failed"
            task.result = result
            task.error = error
            task.decided_at = datetime.now(tz=timezone.utc).isoformat()

            # Release resources
            for resource in task.locked_resources:
                if self._locks.get(resource) == task_id:
                    del self._locks[resource]

            # Decrement agent counter
            count = self._agent_task_counts.get(task.agent_id, 1)
            self._agent_task_counts[task.agent_id] = max(0, count - 1)

        await event_bus.publish(
            Event(
                topic="judge.task.completed",
                payload={
                    "task_id": task_id,
                    "status": task.status,
                    "error": error,
                },
                source="judge_supervisor",
            )
        )

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None) -> list:
        if status:
            return [t for t in self._tasks.values() if t.status == status]
        return list(self._tasks.values())

    def status_summary(self) -> dict:
        counts: Dict[str, int] = {}
        for t in self._tasks.values():
            counts[t.status] = counts.get(t.status, 0) + 1
        return {
            "total_tasks": len(self._tasks),
            "by_status": counts,
            "locked_resources": len(self._locks),
            "active_agents": len(
                {t.agent_id for t in self._tasks.values() if t.status == PENDING}
            ),
        }

    def _reject(self, task: Task, reason: str) -> Task:
        task.status = REJECTED
        task.error = reason
        task.decided_at = datetime.now(tz=timezone.utc).isoformat()
        logger.warning("Task %s rejected: %s", task.task_id, reason)
        return task


# Module-level singleton
judge_supervisor = JudgeSupervisor()
