"""
MemoryStore — async SQLite-backed persistent memory.

Tables:
  conversations  — rolling conversation history per session/agent
  kv             — arbitrary key-value pairs (config, agent state, etc.)
  events         — timestamped event log for audit / replay

Usage:
    store = MemoryStore()
    await store.init()
    await store.add_message("session-1", "user", "Hello")
    messages = await store.get_history("session-1", limit=20)
"""

import asyncio
import json
import logging
import pathlib
import sqlite3
import time
from typing import Any

log = logging.getLogger("memory.store")

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data" / "memory"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DATA_DIR / "memory.db"

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS conversations (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    session   TEXT    NOT NULL,
    agent     TEXT    NOT NULL DEFAULT 'system',
    role      TEXT    NOT NULL,
    content   TEXT    NOT NULL,
    ts        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session, ts);

CREATE TABLE IF NOT EXISTS kv (
    key       TEXT PRIMARY KEY,
    value     TEXT NOT NULL,
    updated   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    type      TEXT    NOT NULL,
    payload   TEXT    NOT NULL DEFAULT '{}',
    ts        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, ts);
"""


class MemoryStore:
    """Thread-safe async SQLite memory store."""

    def __init__(self, db_path: pathlib.Path = _DB_PATH) -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self) -> None:
        """Create tables if they don't exist."""
        await asyncio.get_event_loop().run_in_executor(None, self._init_sync)
        log.info("MemoryStore initialised at %s", self._db_path)

    def _init_sync(self) -> None:
        con = sqlite3.connect(self._db_path)
        try:
            con.executescript(_SCHEMA)
            con.commit()
        finally:
            con.close()

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    async def add_message(
        self, session: str, role: str, content: str, agent: str = "system"
    ) -> None:
        """Append a message to a session's conversation history."""
        ts = int(time.time() * 1000)
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._exec,
                "INSERT INTO conversations(session,agent,role,content,ts) VALUES(?,?,?,?,?)",
                (session, agent, role, content, ts),
            )

    async def get_history(
        self, session: str, limit: int = 50, agent: str | None = None
    ) -> list[dict[str, Any]]:
        """Return the most recent `limit` messages for a session."""
        if agent:
            sql = (
                "SELECT role,content,agent,ts FROM conversations "
                "WHERE session=? AND agent=? ORDER BY ts DESC LIMIT ?"
            )
            params = (session, agent, limit)
        else:
            sql = (
                "SELECT role,content,agent,ts FROM conversations "
                "WHERE session=? ORDER BY ts DESC LIMIT ?"
            )
            params = (session, limit)

        rows = await asyncio.get_event_loop().run_in_executor(
            None, self._query, sql, params
        )
        # Return in chronological order
        rows.reverse()
        return [
            {"role": r[0], "content": r[1], "agent": r[2], "ts": r[3]}
            for r in rows
        ]

    async def clear_history(self, session: str) -> None:
        """Delete all messages for a session."""
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._exec,
                "DELETE FROM conversations WHERE session=?",
                (session,),
            )

    async def count_messages(self, session: str) -> int:
        """Count total messages in a session."""
        rows = await asyncio.get_event_loop().run_in_executor(
            None,
            self._query,
            "SELECT COUNT(*) FROM conversations WHERE session=?",
            (session,),
        )
        return rows[0][0] if rows else 0

    # ------------------------------------------------------------------
    # Key-value store
    # ------------------------------------------------------------------

    async def set(self, key: str, value: Any) -> None:
        """Store a value under `key`. Value is JSON-serialised."""
        payload = json.dumps(value)
        ts = int(time.time() * 1000)
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._exec,
                "INSERT OR REPLACE INTO kv(key,value,updated) VALUES(?,?,?)",
                (key, payload, ts),
            )

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by `key`. Returns `default` if not found."""
        rows = await asyncio.get_event_loop().run_in_executor(
            None,
            self._query,
            "SELECT value FROM kv WHERE key=?",
            (key,),
        )
        if not rows:
            return default
        try:
            return json.loads(rows[0][0])
        except Exception:
            return rows[0][0]

    async def delete(self, key: str) -> None:
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(
                None, self._exec, "DELETE FROM kv WHERE key=?", (key,)
            )

    async def keys(self, prefix: str = "") -> list[str]:
        """List all keys, optionally filtered by prefix."""
        rows = await asyncio.get_event_loop().run_in_executor(
            None,
            self._query,
            "SELECT key FROM kv WHERE key LIKE ? ORDER BY key",
            (prefix + "%",),
        )
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    async def log_event(self, event_type: str, payload: dict | None = None) -> None:
        """Append a typed event to the audit log."""
        ts = int(time.time() * 1000)
        data = json.dumps(payload or {})
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._exec,
                "INSERT INTO events(type,payload,ts) VALUES(?,?,?)",
                (event_type, data, ts),
            )

    async def get_events(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return recent events, optionally filtered by type."""
        if event_type:
            sql = (
                "SELECT type,payload,ts FROM events "
                "WHERE type=? ORDER BY ts DESC LIMIT ?"
            )
            params = (event_type, limit)
        else:
            sql = "SELECT type,payload,ts FROM events ORDER BY ts DESC LIMIT ?"
            params = (limit,)

        rows = await asyncio.get_event_loop().run_in_executor(
            None, self._query, sql, params
        )
        return [
            {"type": r[0], "payload": json.loads(r[1]), "ts": r[2]} for r in rows
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _exec(self, sql: str, params: tuple = ()) -> None:
        con = sqlite3.connect(self._db_path)
        try:
            con.execute(sql, params)
            con.commit()
        finally:
            con.close()

    def _query(self, sql: str, params: tuple = ()) -> list[tuple]:
        con = sqlite3.connect(self._db_path)
        try:
            cur = con.execute(sql, params)
            return cur.fetchall()
        finally:
            con.close()
