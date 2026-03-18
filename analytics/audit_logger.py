"""
Sovereignty AI Studio — Audit Logger
Append-only audit trail for all critical actions.
Writes to the immutable ``audit_logs`` Postgres table.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def log_action(
    *,
    action: str,
    user_id: Optional[str] = None,
    resource: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Append one audit record to the ``audit_logs`` table.

    :param action:     Short action name, e.g. 'auth.login', 'data.export'
    :param user_id:    UUID of the actor (None for system actions)
    :param resource:   Resource identifier (table name, endpoint, file path, …)
    :param details:    Arbitrary JSON-serialisable dict with extra context
    :param ip_address: Client IP address (for auth events)
    """
    try:
        from db.connector import execute_write

        execute_write(
            """
            INSERT INTO audit_logs (user_id, action, resource, details, ip_address, created_at)
            VALUES (%s, %s, %s, %s, %s, to_timestamp(%s))
            """,
            (
                user_id or None,
                str(action),
                resource or None,
                json.dumps(details) if details else None,
                ip_address or None,
                time.time(),
            ),
        )
        logger.info("AUDIT %s user=%s resource=%s", action, user_id, resource)
    except Exception as exc:  # noqa: BLE001
        # Audit failures must never break the main request path,
        # but we log them loudly so they're never silently dropped.
        logger.error("AUDIT LOG FAILED: %s | action=%s user=%s", exc, action, user_id)


def get_audit_logs(
    *,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[dict]:
    """
    Read audit log entries (for the security dashboard).

    :param user_id: Filter by actor UUID
    :param action:  Filter by action prefix (SQL LIKE pattern, e.g. 'auth.%')
    :param limit:   Max rows
    :param offset:  Pagination offset
    :returns:       List of audit log dicts (newest first)
    """
    from db.connector import execute

    conditions = []
    params: list = []
    if user_id:
        conditions.append("user_id = %s")
        params.append(user_id)
    if action:
        conditions.append("action LIKE %s")
        params.append(action if "%" in action else f"{action}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]

    sql = f"""
        SELECT id, user_id, action, resource, details, ip_address, created_at
        FROM audit_logs
        {where}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    return execute(sql, tuple(params))
