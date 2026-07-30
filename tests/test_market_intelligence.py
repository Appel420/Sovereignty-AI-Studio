"""Tests for local-first market intelligence and renderer-safe empty states."""
from __future__ import annotations

from dataclasses import dataclass

from market_intelligence import (
    FeedPolicy,
    FeedRequest,
    LocalMarketCache,
    MarketIntelligenceEngine,
    build_empty_state,
)


@dataclass
class Adapter:
    name: str = "local-fixture"

    def fetch(self, request: FeedRequest):
        return [
            {
                "provider": "Example",
                "model": "model-1",
                "version": "1",
                "pricing": {"input": "0"},
                "capabilities": ["chat"],
                "private_payload": "must be discarded",
            }
        ]


def test_offline_policy_never_calls_adapter_and_returns_empty_cache() -> None:
    class FailingAdapter:
        name = "should-not-run"

        def fetch(self, request):
            raise AssertionError("offline policy called the adapter")

    cache = LocalMarketCache()
    result = MarketIntelligenceEngine(cache).refresh(
        FeedRequest("example"), FeedPolicy(), FailingAdapter()
    )
    assert result.decision.reason == "offline_mode"
    assert result.records == ()
    cache.close()


def test_approved_public_refresh_normalizes_and_caches_only_public_schema() -> None:
    cache = LocalMarketCache()
    policy = FeedPolicy(
        mode="HYBRID",
        public_feed_enabled=True,
        allowed_sources=frozenset({"example"}),
    )
    result = MarketIntelligenceEngine(cache).refresh(
        FeedRequest("example", consent_token="owner-approved"), policy, Adapter(), now=lambda: "now"
    )
    assert result.decision.allowed is True
    assert result.records[0].data_classification == "public"
    assert result.records[0].source == "example"
    assert "private_payload" not in result.records[0].to_json()
    assert len(cache.list(source="example")) == 1
    cache.close()


def test_denied_refresh_uses_local_cache() -> None:
    cache = LocalMarketCache()
    policy = FeedPolicy(mode="HYBRID", public_feed_enabled=True, allowed_sources=frozenset({"example"}))
    engine = MarketIntelligenceEngine(cache)
    engine.refresh(FeedRequest("example", consent_token="approved"), policy, Adapter(), now=lambda: "now")
    result = engine.refresh(FeedRequest("example"), FeedPolicy(), Adapter())
    assert result.cache_used is True
    assert len(result.records) == 1
    assert result.decision.reason == "offline_mode"
    cache.close()


def test_empty_state_never_blocks_dashboard() -> None:
    state = build_empty_state(record_count=0, feed_enabled=False)
    assert state is not None
    assert state.blocking is False
    assert "Connect Feed" in state.actions


def test_empty_state_disappears_when_cache_has_records() -> None:
    assert build_empty_state(record_count=1, feed_enabled=True) is None
