"""
memory/memory_index.py
======================
Searchable memory index with recency + relevance scoring.

The ``MemoryIndex`` wraps a :class:`~memory.memory_store.MemoryStore` and
provides a higher-level ``search`` interface that ranks results by a
combined score::

    score = relevance_weight * keyword_score + recency_weight * recency_score

``keyword_score``
    Fraction of query tokens that appear in the serialised record value.
    Range: 0.0 – 1.0.

``recency_score``
    Exponential decay based on ``updated_at`` age.  A record updated 0 seconds
    ago scores 1.0; one updated ``decay_half_life_secs`` seconds ago scores 0.5.
    Range: 0.0 – 1.0.

Usage::

    index = MemoryIndex(store)
    await index.rebuild()                      # one-time index build
    results = await index.search("weather api", namespace="bridge", top_k=5)
    for scored_record in results:
        print(scored_record.score, scored_record.record.value)
"""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass
from typing import List, Optional

from .memory_store import MemoryRecord, MemoryStore

log = logging.getLogger(__name__)

# Default scoring weights
_DEFAULT_RELEVANCE_WEIGHT: float = 0.6
_DEFAULT_RECENCY_WEIGHT: float = 0.4

# Half-life for recency decay: records 24 h old get score 0.5
_DEFAULT_DECAY_HALF_LIFE_SECS: float = 86_400.0  # 24 hours


@dataclass
class ScoredRecord:
    """A :class:`MemoryRecord` paired with its search relevance score.

    Attributes:
        record: The underlying memory record.
        score:  Combined relevance + recency score in the range 0.0 – 1.0.
    """

    record: MemoryRecord
    score: float


class MemoryIndex:
    """Searchable, scored index over a :class:`MemoryStore`.

    Args:
        store:                The backing store to index.
        relevance_weight:     Weight applied to keyword relevance (0.0 – 1.0).
        recency_weight:       Weight applied to recency score (0.0 – 1.0).
        decay_half_life_secs: Seconds until recency score halves.

    Note:
        ``relevance_weight + recency_weight`` does not have to equal 1.0 —
        the raw weighted sum is used so callers can amplify either dimension.
    """

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        *,
        relevance_weight: float = _DEFAULT_RELEVANCE_WEIGHT,
        recency_weight: float = _DEFAULT_RECENCY_WEIGHT,
        decay_half_life_secs: float = _DEFAULT_DECAY_HALF_LIFE_SECS,
    ) -> None:
        self._store = store or MemoryStore()
        self.relevance_weight = relevance_weight
        self.recency_weight = recency_weight
        self.decay_half_life_secs = decay_half_life_secs
        # In-memory flat list of all indexed records (rebuilt on demand)
        self._index: List[MemoryRecord] = []
        self._last_rebuild: float = 0.0

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    async def rebuild(
        self,
        namespaces: Optional[List[str]] = None,
        *,
        limit_per_namespace: int = 2000,
    ) -> int:
        """Populate the in-memory index from the store.

        Args:
            namespaces:             List of namespaces to index.  When
                                    ``None`` a set of well-known namespaces is
                                    used.
            limit_per_namespace:    Maximum records to load per namespace.

        Returns:
            Total number of records indexed.
        """
        await self._store.initialise()
        default_namespaces = [
            "global",
            "interactions:bridge",
            "interactions:judge",
            "interactions:ai_router",
            "interactions:platform",
            "interactions:voice",
            "interactions:plugin",
        ]
        targets = namespaces or default_namespaces
        all_records: List[MemoryRecord] = []

        for ns in targets:
            records = await self._store.load_namespace(
                ns, limit=limit_per_namespace
            )
            all_records.extend(records)

        self._index = all_records
        self._last_rebuild = time.time()
        log.info("MemoryIndex rebuilt: %d records indexed", len(self._index))
        return len(self._index)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        namespace: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.01,
    ) -> List[ScoredRecord]:
        """Search the index for records relevant to *query*.

        Args:
            query:     Natural-language search string.  Token-split and
                       matched against serialised record values.
            namespace: Restrict results to this namespace.
            top_k:     Maximum number of results to return.
            min_score: Discard results below this combined score threshold.

        Returns:
            List of :class:`ScoredRecord` sorted by score descending.
        """
        if not self._index:
            await self.rebuild()

        tokens = self._tokenize(query)
        if not tokens:
            return []

        now = time.time()
        scored: List[ScoredRecord] = []

        for record in self._index:
            if namespace and record.namespace != namespace:
                continue

            kw_score = self._keyword_score(record, tokens)
            rec_score = self._recency_score(record, now)
            combined = (
                self.relevance_weight * kw_score
                + self.recency_weight * rec_score
            )
            if combined >= min_score:
                scored.append(ScoredRecord(record=record, score=combined))

        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _keyword_score(
        self, record: MemoryRecord, tokens: List[str]
    ) -> float:
        """Compute fraction of query tokens that appear in the record text."""
        text = self._record_to_text(record).lower()
        matches = sum(1 for t in tokens if t in text)
        return matches / len(tokens)

    def _recency_score(self, record: MemoryRecord, now: float) -> float:
        """Compute an exponential-decay recency score in [0, 1].

        Uses: score = 2 ** (-(age / half_life))
        A record updated right now → 1.0; one updated half_life seconds ago → 0.5.
        """
        age_secs = max(0.0, now - record.updated_at)
        exponent = -age_secs / self.decay_half_life_secs
        return math.pow(2.0, exponent)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Split query text into lowercase word tokens (3+ chars)."""
        return [w for w in re.split(r"\W+", text.lower()) if len(w) >= 3]

    @staticmethod
    def _record_to_text(record: MemoryRecord) -> str:
        """Flatten a record into a searchable text string."""
        parts: List[str] = [record.key, record.namespace]
        parts.extend(record.tags)
        value = record.value
        if isinstance(value, dict):
            parts.extend(str(v) for v in value.values())
        else:
            parts.append(str(value))
        return " ".join(parts)
