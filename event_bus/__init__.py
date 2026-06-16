# event_bus/__init__.py

from .event_bus import AsyncEventBus
from .circuit_breaker import SovereignCircuitBreaker

__all__ = ["AsyncEventBus", "SovereignCircuitBreaker", "create_event_bus"]


def create_event_bus(scar, name: str = "event_bus", redis_url: str = None):
    """Create and return a configured AsyncEventBus"""
    return AsyncEventBus(scar=scar, name=name, redis_url=redis_url)
