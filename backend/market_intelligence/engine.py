"""Local-first market intelligence engine.

The engine is deliberately transport-neutral. A caller supplies a public-feed
adapter and explicitly chooses whether policy permits refresh. Records are
normalized and persisted in a local SQLite cache. No credentials, prompts,
private content, telemetry, or network client belongs here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Callable, Iterable, Mapping, Protocol


class PublicFeedAdapter(Protocol):
    name: str

    def fetch(self, request: "FeedRequest") -> Iterable[Mapping[str, Any]]:
        """Return public model metadata only."""


@dataclass(frozen=True, slots=True)
class FeedRequest:
    source: str
    consent_token: str | None = None
    limit: int = 100


@dataclass(frozen=True, slots=True)
class FeedPolicy:
    """Owner-controlled network policy; defaults to local/offline behavior."""

    mode: str = "OFFLINE"
    public_feed_enabled: bool = False
    allowed_sources: frozenset[str] = frozenset()
    require_explicit_consent: bool = True
    policy_version: str = "1.0"

    def decide(self, request: FeedRequest) -> "FeedDecision":
        if self.mode.upper() == "OFFLINE":
            return FeedDecision(False, "offline_mode")
        if not self.public_feed_enabled:
            return FeedDecision(False, "public_feed_disabled")
        if request.source not in self.allowed_sources:
            return FeedDecision(False, "source_not_allowed")
        if self.require_explicit_consent and not request.consent_token:
            return FeedDecision(False, "explicit_consent_required")
        return FeedDecision(True, "approved")


@dataclass(frozen=True, slots=True)
class FeedDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class MarketRecord:
    provider: str
    model: str
    version: str | None = None
    released: str | None = None
    pricing: Mapping[str, Any] = field(default_factory=dict)
    context: Mapping[str, Any] = field(default_factory=dict)
    latency: Mapping[str, Any] = field(default_factory=dict)
    license: str | None = None
    status: str = "unknown"
    capabilities: tuple[str, ...] = ()
    last_updated: str = ""
    source: str = ""
    data_classification: str = "public"
    stored_locally: bool = True

    @classmethod
    def from_public(cls, raw: Mapping[str, Any], *, source: str, now: str) -> "MarketRecord":
        """Normalize an adapter record and discard fields outside the public schema."""
        capabilities = raw.get("capabilities", ())
        if isinstance(capabilities, str):
            capabilities = (capabilities,)
        return cls(
            provider=str(raw.get("provider", "unknown")),
            model=str(raw.get("model", "unknown")),
            version=raw.get("version"),
            released=raw.get("released"),
            pricing=dict(raw.get("pricing") or {}),
            context=dict(raw.get("context") or {}),
            latency=dict(raw.get("latency") or {}),
            license=raw.get("license"),
            status=str(raw.get("status", "unknown")),
            capabilities=tuple(str(value) for value in capabilities),
            last_updated=str(raw.get("last_updated") or now),
            source=source,
            data_classification="public",
            stored_locally=True,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> "MarketRecord":
        raw = json.loads(value)
        raw["pricing"] = dict(raw.get("pricing") or {})
        raw["context"] = dict(raw.get("context") or {})
        raw["latency"] = dict(raw.get("latency") or {})
        raw["capabilities"] = tuple(raw.get("capabilities") or ())
        return cls(**raw)


@dataclass(frozen=True, slots=True)
class RefreshResult:
    source: str
    decision: FeedDecision
    records: tuple[MarketRecord, ...]
    refreshed_at: str | None
    cache_used: bool


class LocalMarketCache:
    """SQLite cache owned by the device; no remote persistence is attempted."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._db = sqlite3.connect(self.path)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS market_records (
                record_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )"""
        )
        self._db.commit()

    def put(self, records: Iterable[MarketRecord]) -> None:
        rows = []
        for record in records:
            key = f"{record.source}:{record.provider}:{record.model}:{record.version or ''}"
            rows.append((key, record.source, record.provider, record.model, record.last_updated, record.to_json()))
        self._db.executemany(
            """INSERT INTO market_records
               (record_key, source, provider, model, updated_at, payload)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(record_key) DO UPDATE SET
                 updated_at=excluded.updated_at, payload=excluded.payload""",
            rows,
        )
        self._db.commit()

    def list(self, *, source: str | None = None) -> tuple[MarketRecord, ...]:
        if source:
            rows = self._db.execute(
                "SELECT payload FROM market_records WHERE source=? ORDER BY provider, model",
                (source,),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT payload FROM market_records ORDER BY provider, model"
            ).fetchall()
        return tuple(MarketRecord.from_json(row[0]) for row in rows)

    def close(self) -> None:
        self._db.close()


class MarketIntelligenceEngine:
    def __init__(self, cache: LocalMarketCache) -> None:
        self.cache = cache

    def refresh(
        self,
        request: FeedRequest,
        policy: FeedPolicy,
        adapter: PublicFeedAdapter,
        *,
        now: Callable[[], str] | None = None,
    ) -> RefreshResult:
        decision = policy.decide(request)
        if not decision.allowed:
            cached = self.cache.list(source=request.source)
            return RefreshResult(request.source, decision, cached, None, bool(cached))

        timestamp = (now or _utc_now)()
        raw_records = adapter.fetch(request)
        records = tuple(
            MarketRecord.from_public(raw, source=request.source, now=timestamp)
            for raw in raw_records
        )
        self.cache.put(records)
        return RefreshResult(request.source, decision, records, timestamp, False)

    def snapshot(self, *, source: str | None = None) -> tuple[MarketRecord, ...]:
        return self.cache.list(source=source)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
