"""
Sovereignty AI Studio — PostgreSQL Connector
Pure psycopg2 — no ORM bloat.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator, List, Optional, Tuple

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2.pool import ThreadedConnectionPool
except ImportError as _err:
    raise ImportError(
        "psycopg2 not installed. Run: pip install psycopg2-binary"
    ) from _err

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sovereignty:password@localhost:9899/sovereignty_db",
)

# Lazy-initialised connection pool (min 1, max 10 connections)
_pool: Optional[ThreadedConnectionPool] = None


def _get_pool() -> ThreadedConnectionPool:
    global _pool  # noqa: PLW0603
    if _pool is None:
        logger.info("Initialising Postgres connection pool → %s", _DATABASE_URL)
        _pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=_DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return _pool


@contextmanager
def get_conn() -> Generator[Any, None, None]:
    """Yield a pooled connection; commits on success, rolls back on error."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def execute(
    sql: str,
    params: Optional[Tuple[Any, ...]] = None,
) -> List[dict]:
    """Execute a query and return all rows as dicts."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            return []


def execute_one(
    sql: str,
    params: Optional[Tuple[Any, ...]] = None,
) -> Optional[dict]:
    """Execute a query and return the first row as a dict, or None."""
    rows = execute(sql, params)
    return rows[0] if rows else None


def execute_write(
    sql: str,
    params: Optional[Tuple[Any, ...]] = None,
) -> int:
    """Execute an INSERT/UPDATE/DELETE and return the number of affected rows."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


def init_schema(schema_path: Optional[str] = None) -> None:
    """Run the schema SQL file (idempotent — uses IF NOT EXISTS)."""
    path = schema_path or os.path.join(
        os.path.dirname(__file__), "schema.sql"
    )
    with open(path, encoding="utf-8") as fh:
        sql = fh.read()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    logger.info("Schema initialised from %s", path)
