"""
Telemetry API endpoints — system health, AI metrics, agent status.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.dependencies import get_current_active_user
from app.models.user import User
from app.services.telemetry import telemetry
from app.services.agent_registry import agent_registry
from app.services.judge_supervisor import judge_supervisor
from app.services.event_bus import event_bus

router = APIRouter()


@router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(get_current_active_user),
):
    """
    Return system health and agent status metrics.
    Includes AI provider request counts, latency, error rates, agent status.
    """
    metrics = telemetry.get_metrics()
    agents = agent_registry.summary()
    judge = judge_supervisor.status_summary()

    return {
        **metrics,
        "agents": agents,
        "judge": judge,
        "event_bus": {
            "queue_size": event_bus.queue_size,
            "subscriber_count": event_bus.subscriber_count,
        },
    }


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Return metrics in Prometheus text format for scraping."""
    return PlainTextResponse(
        content=telemetry.prometheus_format(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/agents")
async def list_agents(
    agent_type: str = None,
    current_user: User = Depends(get_current_active_user),
):
    """List all registered agents with their health status."""
    agents = agent_registry.list_agents(agent_type=agent_type)
    return {
        "items": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "type": a.agent_type,
                "status": a.status,
                "capabilities": a.capabilities,
                "version": a.version,
                "last_heartbeat": a.last_heartbeat,
                "error_count": a.error_count,
            }
            for a in agents
        ],
        "total": len(agents),
        "summary": agent_registry.summary(),
    }


@router.get("/judge/tasks")
async def get_judge_tasks(
    status: str = None,
    current_user: User = Depends(get_current_active_user),
):
    """Return judge supervisor task queue status."""
    tasks = judge_supervisor.list_tasks(status=status)
    return {
        "items": [
            {
                "task_id": t.task_id,
                "agent_id": t.agent_id,
                "action": t.action,
                "status": t.status,
                "error": t.error,
                "submitted_at": t.submitted_at,
                "decided_at": t.decided_at,
            }
            for t in tasks
        ],
        "summary": judge_supervisor.status_summary(),
    }
