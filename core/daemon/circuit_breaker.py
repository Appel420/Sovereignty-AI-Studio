"""
circuit_breaker.py

A simple, asyncio-friendly circuit breaker implementation.

Features:
- CLOSED / OPEN / HALF_OPEN states
- sliding-window failure counting (timestamps)
- configurable failure_threshold, window_seconds, cooldown_seconds, half_open_max_calls
- async context manager and decorator to protect coroutines
- exposes hooks for state changes (useful for metrics)
- thread-safe via asyncio.Lock

Usage:
cb = CircuitBreaker(failure_threshold=5, window_seconds=60, cooldown_seconds=30)

async with cb:
    await some_network_call()

# decorator
@cb.decorate
async def protected():
    ...
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from enum import Enum
from typing import Any, Awaitable, Callable, Deque, Optional


class State(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


StateChangeHook = Callable[[State, State], None]  # (old, new)


class CircuitOpenError(Exception):
    """Raised when attempting to call while circuit is open/half-open disallowed."""
    pass


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        window_seconds: int = 60,
        cooldown_seconds: int = 30,
        half_open_max_calls: int = 1,
        on_state_change: Optional[StateChangeHook] = None,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self.failure_threshold = int(failure_threshold)
        self.window_seconds = int(window_seconds)
        self.cooldown_seconds = int(cooldown_seconds)
        self.half_open_max_calls = int(half_open_max_calls)
        self._on_state_change = on_state_change
        self._time = time_fn or time.time

        self._state: State = State.CLOSED
        self._lock = asyncio.Lock()
        self._failures: Deque[float] = deque()
        self._opened_at: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> State:
        return self._state

    def _set_state(self, new: State) -> None:
        old = self._state
        if old is new:
            return
        self._state = new
        if new is State.OPEN:
            self._opened_at = self._time()
        if new is State.CLOSED:
            self._opened_at = None
            self._failures.clear()
            self._half_open_calls = 0
        if self._on_state_change:
            try:
                self._on_state_change(old, new)
            except Exception:
                pass

    def _prune_failures(self) -> None:
        cutoff = self._time() - self.window_seconds
        while self._failures and self._failures[0] < cutoff:
            self._failures.popleft()

    async def _before_call(self) -> None:
        async with self._lock:
            now = self._time()
            if self._state is State.OPEN:
                assert self._opened_at is not None
                if now - self._opened_at >= self.cooldown_seconds:
                    # move to half-open and allow trial calls
                    self._set_state(State.HALF_OPEN)
                    self._half_open_calls = 0
                else:
                    raise CircuitOpenError("Circuit is open")
            if self._state is State.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitOpenError("Circuit is half-open and trial calls exhausted")
                self._half_open_calls += 1

    async def _after_call_success(self) -> None:
        async with self._lock:
            if self._state is State.HALF_OPEN:
                # success in half-open -> close circuit
                self._set_state(State.CLOSED)

    async def _after_call_failure(self) -> None:
        async with self._lock:
            now = self._time()
            self._failures.append(now)
            self._prune_failures()
            if self._state in (State.CLOSED, State.HALF_OPEN):
                if len(self._failures) >= self.failure_threshold:
                    self._set_state(State.OPEN)

    async def call(self, coro: Awaitable[Any]) -> Any:
        """
        Execute the given coroutine under circuit breaker protection.
        Raises CircuitOpenError if circuit is open.
        """
        await self._before_call()
        try:
            res = await coro
        except Exception:
            await self._after_call_failure()
            raise
        else:
            await self._after_call_success()
            return res

    # Async context manager ------------------------------------------------
    async def __aenter__(self) -> "CircuitBreaker":
        await self._before_call()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> Optional[bool]:
        if exc is None:
            await self._after_call_success()
        else:
            await self._after_call_failure()
        # Do not suppress exceptions
        return False

    # Decorator -----------------------------------------------------------
    def decorate(self, fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        async def wrapper(*args, **kwargs):
            await self._before_call()
            try:
                res = await fn(*args, **kwargs)
            except Exception:
                await self._after_call_failure()
                raise
            else:
                await self._after_call_success()
                return res
        return wrapper

    # Manual controls ----------------------------------------------------
    async def force_open(self) -> None:
        async with self._lock:
            self._set_state(State.OPEN)

    async def force_close(self) -> None:
        async with self._lock:
            self._set_state(State.CLOSED)

    async def reset(self) -> None:
        await self.force_close()

