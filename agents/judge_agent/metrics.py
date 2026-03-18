"""Prometheus metrics for the Judge Agent.

Exposes three counters:
- ``tasks_approved_total``
- ``tasks_rejected_total``
- ``tasks_released_total``

A lightweight HTTP server is started on ``JUDGE_METRICS_PORT`` (default 8000)
so Prometheus can scrape the ``/metrics`` endpoint.
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)

_METRICS_PORT = int(os.getenv("JUDGE_METRICS_PORT", "8000"))

# ---------------------------------------------------------------------------
# Metric objects — created lazily so the import doesn't fail when
# prometheus_client is not installed (test environments, etc.).
# ---------------------------------------------------------------------------

tasks_approved_total = None
tasks_rejected_total = None
tasks_released_total = None
_server_started = False


def _init_metrics() -> None:
    global tasks_approved_total, tasks_rejected_total, tasks_released_total
    try:
        from prometheus_client import Counter  # type: ignore

        tasks_approved_total = Counter(
            "tasks_approved_total",
            "Total number of tasks approved by the Judge",
            ["agent_id"],
        )
        tasks_rejected_total = Counter(
            "tasks_rejected_total",
            "Total number of tasks rejected by the Judge",
            ["agent_id"],
        )
        tasks_released_total = Counter(
            "tasks_released_total",
            "Total number of resource locks released by the Judge",
            ["agent_id"],
        )
    except ImportError:
        logger.warning(
            "prometheus_client not installed; metrics will be no-ops"
        )


def start_metrics_server() -> None:
    """Start the Prometheus HTTP metrics server in a background daemon thread."""
    global _server_started
    if _server_started:
        return
    _init_metrics()
    try:
        from prometheus_client import start_http_server  # type: ignore

        t = threading.Thread(
            target=start_http_server,
            args=(_METRICS_PORT,),
            daemon=True,
            name="prometheus-metrics",
        )
        t.start()
        _server_started = True
        logger.info("Prometheus metrics server started on port %d", _METRICS_PORT)
    except Exception as exc:
        logger.warning("Could not start metrics server: %s", exc)


def inc_approved(agent_id: str) -> None:
    if tasks_approved_total is not None:
        tasks_approved_total.labels(agent_id=agent_id).inc()


def inc_rejected(agent_id: str) -> None:
    if tasks_rejected_total is not None:
        tasks_rejected_total.labels(agent_id=agent_id).inc()


def inc_released(agent_id: str) -> None:
    if tasks_released_total is not None:
        tasks_released_total.labels(agent_id=agent_id).inc()
