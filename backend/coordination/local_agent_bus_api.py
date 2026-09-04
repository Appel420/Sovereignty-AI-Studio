"""Compatibility exports for the local coordination bus."""
from .local_agent_bus import AgentMessage, BusError, LocalAgentBus, encode_message

__all__ = ["AgentMessage", "BusError", "LocalAgentBus", "encode_message"]
