"""Abstract base class for streaming platform connectors."""

import abc
from typing import AsyncIterator, Optional


class PlatformConnector(abc.ABC):
    """Defines the interface every platform connector must implement."""

    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish a connection to the platform."""

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the connection."""

    @abc.abstractmethod
    async def read_chat(self) -> AsyncIterator[dict]:
        """Yield chat messages as they arrive.

        Each yielded item is a dict with at minimum::

            {"user": str, "text": str, "platform": str}
        """

    @abc.abstractmethod
    async def send_message(self, text: str, channel: Optional[str] = None) -> None:
        """Send *text* to the platform's chat channel."""
