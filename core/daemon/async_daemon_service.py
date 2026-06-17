"""Async daemon service helpers."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class DaemonState:
    running: bool = False
    started_at: float | None = None
    stopped_at: float | None = None


class AsyncDaemonService:
    """Small lifecycle wrapper for async background services."""

    def __init__(self, name: str = "async-daemon") -> None:
        self.name = name
        self.state = DaemonState()

    async def on_start(self) -> None:
        return None

    async def on_stop(self) -> None:
        return None

    async def start(self) -> None:
        if self.state.running:
            return
        self.state.running = True
        self.state.started_at = time.time()
        await self.on_start()

    async def stop(self) -> None:
        if not self.state.running and self.state.stopped_at is not None:
            return
        try:
            await self.on_stop()
        finally:
            self.state.running = False
            self.state.stopped_at = time.time()

    async def run(self) -> None:
        await self.start()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            raise
        finally:
            await self.stop()


Service = AsyncDaemonService