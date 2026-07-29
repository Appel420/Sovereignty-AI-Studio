"""Local-first public market-intelligence contracts.

This package contains policy, normalization, caching, and UI empty-state
contracts only. Adapters are injected by the local runtime; this module never
performs network calls and never receives private user data.
"""
from .engine import (
    FeedDecision,
    FeedPolicy,
    FeedRequest,
    MarketIntelligenceEngine,
    MarketRecord,
    RefreshResult,
)
from .empty_state import EmptyState, build_empty_state

__all__ = [
    "EmptyState",
    "FeedDecision",
    "FeedPolicy",
    "FeedRequest",
    "MarketIntelligenceEngine",
    "MarketRecord",
    "RefreshResult",
    "build_empty_state",
]
