"""Regression test for the public market-intelligence package API."""
from market_intelligence import LocalMarketCache


def test_local_market_cache_is_exported_from_package_root() -> None:
    cache = LocalMarketCache()
    assert cache.list() == ()
    cache.close()
