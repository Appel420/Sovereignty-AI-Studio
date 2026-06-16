# event_bus/__init__.py

from . import bus

__all__ = ["bus", "create_event_bus"]


def create_event_bus(scar, name: str = "event_bus", redis_url: str = None):
    """Create and return a configured AsyncEventBus"""
    _ = (scar, name, redis_url)
    return bus
