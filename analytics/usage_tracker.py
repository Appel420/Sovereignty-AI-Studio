"""
Sovereignty AI Studio — Usage Tracker
Records AI call tokens and provider usage per user/org/project.
Writes to Postgres via db.connector — no external analytics SaaS.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def record_usage(
    *,
    user_id: str,
    org_id: str,
    tokens: int,
    provider: str,
    project_id: Optional[str] = None,
    model: Optional[str] = None,
    ts: Optional[float] = None,
) -> None:
    """
    Persist one usage record to the ``usage`` table.

    :param user_id:    UUID of the requesting user
    :param org_id:     UUID of the organisation
    :param tokens:     Number of tokens consumed
    :param provider:   Sovereign provider used (e.g. 'local_gguf')
    :param project_id: Optional project UUID
    :param model:      Optional model identifier
    :param ts:         Unix timestamp (default: now)
    """
    try:
        from db.connector import execute_write

        execute_write(
            """
            INSERT INTO usage (user_id, org_id, project_id, tokens, provider, model, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, to_timestamp(%s))
            """,
            (
                user_id or None,
                org_id or None,
                project_id or None,
                max(0, int(tokens)),
                str(provider),
                model or None,
                ts or time.time(),
            ),
        )
        logger.debug(
            "Usage recorded: user=%s org=%s tokens=%d provider=%s",
            user_id, org_id, tokens, provider,
        )
    except Exception as exc:  # noqa: BLE001
        # Usage recording must never crash the main request path
        logger.warning("Failed to record usage: %s", exc)


def get_usage_summary(
    *,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
) -> list:
    """
    Return aggregated usage rows for an org/user/project.

    :param org_id:     Filter by organisation UUID
    :param user_id:    Filter by user UUID
    :param project_id: Filter by project UUID
    :param limit:      Max rows to return
    :returns:          List of dicts: {provider, model, total_tokens, call_count, date}
    """
    from db.connector import execute

    conditions = []
    params: list = []
    if org_id:
        conditions.append("org_id = %s")
        params.append(org_id)
    if user_id:
        conditions.append("user_id = %s")
        params.append(user_id)
    if project_id:
        conditions.append("project_id = %s")
        params.append(project_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    sql = f"""
        SELECT
            provider,
            model,
            SUM(tokens)   AS total_tokens,
            COUNT(*)      AS call_count,
            DATE(created_at) AS date
        FROM usage
        {where}
        GROUP BY provider, model, DATE(created_at)
        ORDER BY date DESC
        LIMIT %s
    """
    return execute(sql, tuple(params))
