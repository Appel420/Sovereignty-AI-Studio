"""
memory/memory_store.py
======================
Core persistent memory store for Sovereignty AI Studio.

Design
------
- **Primary store**: SQLite (via the stdlib ``sqlite3`` / ``aiosqlite``) so that
  memory survives process restarts without any external service dependency.
- **Fast-path cache**: an in-process Python dict keyed by ``namespace:key`` so
  hot reads (e.g. frequently re-read agent context) never touch disk.
- **Graceful degradation**: if ``aiosqlite`` is not installed the store falls
  back to synchronous stdlib ``sqlite3``.  This keeps the module usable in
  minimal environments (CI, local dev without full requirements installed).

Schema (SQLite)
---------------
    memory(
        namespace  TEXT,
        key        TEXT,
        value      TEXT,   -- JSON-serialised
        tags       TEXT,   -- JSON array of strings
        created_at REAL,   -- Unix timestamp
        updated_at REAL,
        PRIMARY KEY (namespace, key)
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional async SQLite backend
# ---------------------------------------------------------------------------
try:
    import aiosqlite  # type: ignore

    _AIOSQLITE_OK = True
except ImportError:
    _AIOSQLITE_OK = False
    log.warning(
        "aiosqlite not installed — memory will fall back to synchronous SQLite. "
        "Install with: pip install aiosqlite"
    )

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
ROOT_DIR = pathlib.Path(__file__).parent.parent
MEMORY_DIR = ROOT_DIR / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = MEMORY_DIR / "sovereignty_memory.db"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class MemoryRecord:
    """A single persisted memory entry.

    Attributes:
        namespace:   Logical grouping, e.g. ``"bridge"``, ``"agent:judge"``.
        key:         Unique identifier within the namespace.
        value:       Arbitrary JSON-serialisable payload.
        tags:        Optional labels for search/filtering.
        created_at:  Unix timestamp of first write.
        updated_at:  Unix timestamp of last write.
    """

    namespace: str
    key: str
    value: Any
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict representation suitable for JSON serialisation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        """Reconstruct a MemoryRecord from a plain dict."""
        return cls(**data)


# ---------------------------------------------------------------------------
# MemoryStore
# ---------------------------------------------------------------------------
class MemoryStore:
    """Async-safe persistent memory store backed by SQLite.

    Args:
        db_path:   Path to the SQLite database file.  Defaults to
                   ``data/memory/sovereignty_memory.db``.
        namespace: Default namespace used when ``namespace`` is not specified
                   in individual call arguments.  Defaults to ``"global"``.

    Example::

        store = MemoryStore(namespace="bridge")
        await store.initialise()
        await store.save("last_prompt", {"text": "Hello", "agent": "judge"})
        record = await store.load("last_prompt")
        print(record.value)          # {"text": "Hello", "agent": "judge"}
    """

    def __init__(
        self,
        db_path: pathlib.Path = DEFAULT_DB_PATH,
        namespace: str = "global",
    ) -> None:
        self.db_path = db_path
        self.default_namespace = namespace
        # In-process LRU-style cache: (namespace, key) → MemoryRecord
        self._cache: Dict[tuple, MemoryRecord] = {}
        self._initialised = False
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialise(self) -> None:
        """Create the database schema if it does not already exist.

        Must be called before any read/write operations.  Calling it more
        than once is safe (idempotent).
        """
        if self._initialised:
            return
        async with self._lock:
            if self._initialised:
                return
            await self._create_schema()
            self._initialised = True
            log.info("MemoryStore initialised at %s", self.db_path)

    async def _create_schema(self) -> None:
        """Create the ``memory`` table if absent."""
        ddl = """
        CREATE TABLE IF NOT EXISTS memory (
            namespace  TEXT    NOT NULL,
            key        TEXT    NOT NULL,
            value      TEXT    NOT NULL,
            tags       TEXT    NOT NULL DEFAULT '[]',
            created_at REAL    NOT NULL,
            updated_at REAL    NOT NULL,
            PRIMARY KEY (namespace, key)
        );
        CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory(namespace);
        CREATE INDEX IF NOT EXISTS idx_memory_tags      ON memory(tags);
        CREATE INDEX IF NOT EXISTS idx_memory_updated   ON memory(updated_at DESC);
        """
        if _AIOSQLITE_OK:
            async with aiosqlite.connect(self.db_path) as db:
                await db.executescript(ddl)
                await db.commit()
        else:
            conn = sqlite3.connect(self.db_path)
            conn.executescript(ddl)
            conn.commit()
            conn.close()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def save(
        self,
        key: str,
        value: Any,
        *,
        namespace: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryRecord:
        """Persist *value* under *namespace*:*key*.

        If a record already exists for the (namespace, key) pair its value
        and ``updated_at`` are updated in place; ``created_at`` is preserved.

        Args:
            key:       Identifier for this memory entry.
            value:     Any JSON-serialisable object.
            namespace: Override the instance default namespace.
            tags:      Optional list of string labels.

        Returns:
            The saved :class:`MemoryRecord`.
        """
        if not self._initialised:
            await self.initialise()

        ns = namespace or self.default_namespace
        now = time.time()
        existing = self._cache.get((ns, key))

        record = MemoryRecord(
            namespace=ns,
            key=key,
            value=value,
            tags=tags or [],
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )

        await self._upsert(record)
        self._cache[(ns, key)] = record
        log.debug("MemoryStore.save [%s:%s]", ns, key)
        return record

    async def _upsert(self, record: MemoryRecord) -> None:
        """Write *record* to the backing store."""
        sql = """
        INSERT INTO memory (namespace, key, value, tags, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(namespace, key) DO UPDATE SET
            value      = excluded.value,
            tags       = excluded.tags,
            updated_at = excluded.updated_at
        """
        params = (
            record.namespace,
            record.key,
            json.dumps(record.value),
            json.dumps(record.tags),
            record.created_at,
            record.updated_at,
        )
        if _AIOSQLITE_OK:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(sql, params)
                await db.commit()
        else:
            conn = sqlite3.connect(self.db_path)
            conn.execute(sql, params)
            conn.commit()
            conn.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def load(
        self,
        key: str,
        *,
        namespace: Optional[str] = None,
    ) -> Optional[MemoryRecord]:
        """Retrieve a single memory record by *namespace* + *key*.

        Returns ``None`` when no matching record exists.

        Args:
            key:       Identifier to look up.
            namespace: Override the instance default namespace.

        Returns:
            A :class:`MemoryRecord` or ``None``.
        """
        if not self._initialised:
            await self.initialise()

        ns = namespace or self.default_namespace

        # Fast-path: serve from in-process cache
        cached = self._cache.get((ns, key))
        if cached is not None:
            return cached

        row = await self._fetch_one(ns, key)
        if row is None:
            return None

        record = self._row_to_record(row)
        self._cache[(ns, key)] = record
        return record

    async def _fetch_one(self, namespace: str, key: str) -> Optional[tuple]:
        """Return a raw DB row for (namespace, key) or None."""
        sql = "SELECT namespace, key, value, tags, created_at, updated_at FROM memory WHERE namespace=? AND key=?"
        if _AIOSQLITE_OK:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(sql, (namespace, key)) as cursor:
                    return await cursor.fetchone()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(sql, (namespace, key))
            row = cursor.fetchone()
            conn.close()
            return row

    async def load_namespace(
        self,
        namespace: Optional[str] = None,
        *,
        limit: int = 500,
    ) -> List[MemoryRecord]:
        """Load all records in *namespace*, newest first.

        Args:
            namespace: Override the instance default namespace.
            limit:     Maximum number of records to return.

        Returns:
            List of :class:`MemoryRecord` objects sorted by ``updated_at DESC``.
        """
        if not self._initialised:
            await self.initialise()

        ns = namespace or self.default_namespace
        sql = (
            "SELECT namespace, key, value, tags, created_at, updated_at "
            "FROM memory WHERE namespace=? ORDER BY updated_at DESC LIMIT ?"
        )
        rows = await self._fetch_many(sql, (ns, limit))
        records = [self._row_to_record(r) for r in rows]
        for rec in records:
            self._cache[(rec.namespace, rec.key)] = rec
        return records

    async def search_by_tags(
        self,
        tags: List[str],
        *,
        namespace: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryRecord]:
        """Return records that contain *any* of the given tags.

        Uses a simple JSON text-search — not a full-text index.  Suitable
        for small-to-medium datasets (< 100 k rows).

        Args:
            tags:      Tags to match.
            namespace: Restrict to this namespace when provided.
            limit:     Maximum records to return.
        """
        if not self._initialised:
            await self.initialise()

        ns = namespace or self.default_namespace
        conditions = " OR ".join(["tags LIKE ?" for _ in tags])
        params: list = [f'%"{t}"%' for t in tags]
        if namespace:
            sql = (
                f"SELECT namespace, key, value, tags, created_at, updated_at "
                f"FROM memory WHERE namespace=? AND ({conditions}) "
                f"ORDER BY updated_at DESC LIMIT ?"
            )
            params = [ns, *params, limit]
        else:
            sql = (
                f"SELECT namespace, key, value, tags, created_at, updated_at "
                f"FROM memory WHERE ({conditions}) ORDER BY updated_at DESC LIMIT ?"
            )
            params = [*params, limit]

        rows = await self._fetch_many(sql, params)
        return [self._row_to_record(r) for r in rows]

    async def delete(
        self,
        key: str,
        *,
        namespace: Optional[str] = None,
    ) -> bool:
        """Delete a record. Returns True if a row was deleted, False otherwise."""
        if not self._initialised:
            await self.initialise()

        ns = namespace or self.default_namespace
        sql = "DELETE FROM memory WHERE namespace=? AND key=?"
        deleted = await self._execute_returning_rowcount(sql, (ns, key))
        self._cache.pop((ns, key), None)
        return deleted > 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _fetch_many(self, sql: str, params: tuple | list) -> List[tuple]:
        if _AIOSQLITE_OK:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(sql, params) as cursor:
                    return await cursor.fetchall()
        else:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(sql, params).fetchall()
            conn.close()
            return rows

    async def _execute_returning_rowcount(
        self, sql: str, params: tuple | list
    ) -> int:
        if _AIOSQLITE_OK:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(sql, params)
                await db.commit()
                return cursor.rowcount
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(sql, params)
            conn.commit()
            count = cursor.rowcount
            conn.close()
            return count

    @staticmethod
    def _row_to_record(row: tuple) -> MemoryRecord:
        """Convert a raw SQLite row tuple to a :class:`MemoryRecord`."""
        namespace, key, value_json, tags_json, created_at, updated_at = row
        return MemoryRecord(
            namespace=namespace,
            key=key,
            value=json.loads(value_json),
            tags=json.loads(tags_json),
            created_at=created_at,
            updated_at=updated_at,
        )
