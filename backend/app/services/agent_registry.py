"""
Agent registry — tracks all active agents with health monitoring.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    agent_id: str
    name: str
    agent_type: str              # "ai", "system", "plugin", "bridge"
    capabilities: List[str]
    version: str = "1.0.0"
    status: str = "idle"         # idle, busy, error, offline
    health_check_fn: Optional[Callable] = None
    last_heartbeat: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    error_count: int = 0
    metadata: Dict = field(default_factory=dict)


class AgentRegistry:
    """
    Central registry for all system agents.

    Features:
    - Register/deregister agents
    - Heartbeat tracking
    - Health monitoring with configurable intervals
    - Query by type or capability
    """

    def __init__(self, heartbeat_timeout_seconds: int = 60):
        self._agents: Dict[str, AgentInfo] = {}
        self._heartbeat_timeout = heartbeat_timeout_seconds
        self._monitor_task: Optional[asyncio.Task] = None

    def register(self, agent: AgentInfo) -> None:
        self._agents[agent.agent_id] = agent
        logger.info(
            "Agent registered: %s (%s) type=%s",
            agent.agent_id, agent.name, agent.agent_type,
        )

    def deregister(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("Agent deregistered: %s", agent_id)
            return True
        return False

    def heartbeat(self, agent_id: str, status: str = "idle") -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.last_heartbeat = datetime.now(tz=timezone.utc).isoformat()
        agent.status = status
        return True

    def set_status(self, agent_id: str, status: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = status

    def get(self, agent_id: str) -> Optional[AgentInfo]:
        return self._agents.get(agent_id)

    def list_agents(
        self,
        agent_type: Optional[str] = None,
        capability: Optional[str] = None,
    ) -> List[AgentInfo]:
        agents = list(self._agents.values())
        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        return agents

    def get_healthy_agents(self) -> List[AgentInfo]:
        return [a for a in self._agents.values() if a.status not in {"error", "offline"}]

    async def run_health_checks(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for agent_id, agent in self._agents.items():
            if agent.health_check_fn:
                try:
                    result = agent.health_check_fn()
                    if asyncio.iscoroutine(result):
                        result = await result
                    results[agent_id] = bool(result)
                    agent.status = "idle" if result else "error"
                    if not result:
                        agent.error_count += 1
                except Exception as exc:
                    results[agent_id] = False
                    agent.status = "error"
                    agent.error_count += 1
                    logger.warning("Health check failed for %s: %s", agent_id, exc)
            else:
                results[agent_id] = agent.status not in {"error", "offline"}
        return results

    async def start_monitoring(self, interval_seconds: int = 30) -> None:
        if self._monitor_task:
            return
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval_seconds)
        )

    async def stop_monitoring(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_loop(self, interval: int) -> None:
        while True:
            try:
                await asyncio.sleep(interval)
                await self.run_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Agent monitor error: %s", exc)

    def summary(self) -> dict:
        by_status: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for a in self._agents.values():
            by_status[a.status] = by_status.get(a.status, 0) + 1
            by_type[a.agent_type] = by_type.get(a.agent_type, 0) + 1
        return {
            "total": len(self._agents),
            "by_status": by_status,
            "by_type": by_type,
        }


# Module-level singleton
agent_registry = AgentRegistry()
