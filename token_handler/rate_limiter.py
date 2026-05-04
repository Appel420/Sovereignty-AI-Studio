"""
token_handler/rate_limiter.py
==============================
Per-token / per-user sliding-window rate limiter for Sovereignty AI Studio.

Design
------
Uses a **sliding window counter** (as opposed to a fixed window) so bursts
at window boundaries are handled fairly.  Counters are stored in an
in-process dict keyed by a ``(subject, window_start)`` tuple.

When a Redis URL is configured (``REDIS_URL`` env var) the limiter switches
to a Redis-backed sliding window for cross-process / cross-instance limiting.
The Redis key format is ``rl:{subject}`` with a TTL equal to the window size.

Usage::

    limiter = RateLimiter(requests_per_minute=60)

    # In an async handler:
    try:
        await limiter.check("user:alice")
    except RateLimitExceeded as exc:
        # Return HTTP 429 or WS error to client
        print(exc.retry_after_seconds)
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Redis support (aioredis already in requirements.txt)
# ---------------------------------------------------------------------------
try:
    import aioredis  # type: ignore

    _REDIS_OK = True
except ImportError:
    _REDIS_OK = False

_REDIS_URL = os.environ.get("REDIS_URL", "")


class RateLimitExceeded(Exception):
    """Raised when a subject has exceeded their allowed request rate.

    Attributes:
        subject:              The identity that was rate-limited.
        retry_after_seconds:  Seconds until the subject may retry.
    """

    def __init__(self, subject: str, retry_after_seconds: float) -> None:
        self.subject = subject
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Rate limit exceeded for '{subject}'. "
            f"Retry after {retry_after_seconds:.1f}s."
        )


@dataclass
class RateLimitPolicy:
    """Configurable rate-limit policy for a subject or group.

    Attributes:
        requests_per_window: Maximum requests allowed within *window_seconds*.
        window_seconds:      Length of the sliding window in seconds.
        burst_multiplier:    Allow up to ``requests_per_window * burst_multiplier``
                             requests in any single second (burst headroom).
    """

    requests_per_window: int = 60
    window_seconds: float = 60.0
    burst_multiplier: float = 1.5


# Default policy applied to all subjects unless overridden
_DEFAULT_POLICY = RateLimitPolicy()


class RateLimiter:
    """Sliding-window rate limiter with per-subject policy overrides.

    Args:
        requests_per_minute: Default request limit per minute.
        window_seconds:      Sliding window duration in seconds.
        redis_url:           Optional Redis URL for cross-process limiting.
                             Defaults to the ``REDIS_URL`` environment variable.

    Example::

        limiter = RateLimiter(requests_per_minute=100)
        limiter.set_policy("admin:root", RateLimitPolicy(requests_per_window=1000))

        await limiter.check("user:alice")      # raises RateLimitExceeded if over
        remaining = await limiter.remaining("user:alice")
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        window_seconds: float = 60.0,
        redis_url: Optional[str] = None,
    ) -> None:
        self._default_policy = RateLimitPolicy(
            requests_per_window=requests_per_minute,
            window_seconds=window_seconds,
        )
        # Per-subject policy overrides
        self._policies: Dict[str, RateLimitPolicy] = {}
        # In-process sliding window counters: subject → list of request timestamps
        self._counters: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._redis: Optional[object] = None
        self._redis_url = redis_url or _REDIS_URL
        self._redis_initialised = False

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def set_policy(self, subject: str, policy: RateLimitPolicy) -> None:
        """Override the rate-limit policy for a specific subject.

        Args:
            subject: Subject identifier (e.g. ``"user:alice"``).
            policy:  Custom :class:`RateLimitPolicy` to apply.
        """
        self._policies[subject] = policy
        log.debug(
            "Rate limit policy set for '%s': %d req / %gs",
            subject,
            policy.requests_per_window,
            policy.window_seconds,
        )

    def get_policy(self, subject: str) -> RateLimitPolicy:
        """Return the effective policy for *subject* (falls back to default)."""
        return self._policies.get(subject, self._default_policy)

    # ------------------------------------------------------------------
    # Core check
    # ------------------------------------------------------------------

    async def check(self, subject: str) -> None:
        """Assert that *subject* is within their rate limit.

        This method is a side-effecting check: it records the current request
        timestamp in the sliding window.  Call it for every inbound request.

        Args:
            subject: Identity to check (e.g. a JWT ``sub`` claim).

        Raises:
            :class:`RateLimitExceeded`: If the subject has exceeded their limit.
        """
        policy = self.get_policy(subject)

        if self._redis_url and _REDIS_OK:
            await self._check_redis(subject, policy)
        else:
            await self._check_local(subject, policy)

    async def remaining(self, subject: str) -> Tuple[int, float]:
        """Return the remaining request allowance for *subject*.

        Returns:
            A ``(count_remaining, window_reset_seconds)`` tuple where
            ``window_reset_seconds`` is the seconds until the oldest request
            in the window expires.
        """
        policy = self.get_policy(subject)
        now = time.time()
        cutoff = now - policy.window_seconds

        async with self._lock:
            window = [t for t in self._counters[subject] if t > cutoff]
            used = len(window)
            remaining_count = max(0, policy.requests_per_window - used)
            reset_in = (window[0] + policy.window_seconds - now) if window else 0.0

        return remaining_count, max(0.0, reset_in)

    # ------------------------------------------------------------------
    # In-process sliding window
    # ------------------------------------------------------------------

    async def _check_local(self, subject: str, policy: RateLimitPolicy) -> None:
        """Sliding-window check using in-process counters."""
        now = time.time()
        cutoff = now - policy.window_seconds

        async with self._lock:
            # Prune timestamps outside the window
            window = [t for t in self._counters[subject] if t > cutoff]
            if len(window) >= policy.requests_per_window:
                # Calculate when the oldest request will fall out of the window
                retry_after = window[0] + policy.window_seconds - now
                raise RateLimitExceeded(
                    subject=subject,
                    retry_after_seconds=math.ceil(retry_after),
                )
            window.append(now)
            self._counters[subject] = window

    # ------------------------------------------------------------------
    # Redis sliding window
    # ------------------------------------------------------------------

    async def _ensure_redis(self) -> Optional[object]:
        """Lazily initialise the Redis client."""
        if self._redis_initialised:
            return self._redis
        self._redis_initialised = True
        if not self._redis_url or not _REDIS_OK:
            return None
        try:
            self._redis = await aioredis.from_url(self._redis_url)
            log.info("RateLimiter connected to Redis at %s", self._redis_url)
        except Exception as exc:  # noqa: BLE001
            log.warning("Redis unavailable for RateLimiter (%s); using local mode", exc)
            self._redis = None
        return self._redis

    async def _check_redis(
        self, subject: str, policy: RateLimitPolicy
    ) -> None:
        """Sliding-window check backed by Redis sorted sets."""
        redis = await self._ensure_redis()
        if redis is None:
            # Fall back gracefully to in-process check
            await self._check_local(subject, policy)
            return

        key = f"rl:{subject}"
        now = time.time()
        cutoff = now - policy.window_seconds

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, int(policy.window_seconds) + 1)
            results = await pipe.execute()
            count_after_prune = results[1]  # Count before the current request

            if count_after_prune >= policy.requests_per_window:
                # Find the oldest timestamp to calculate retry_after
                oldest = await redis.zrange(key, 0, 0, withscores=True)
                retry_after = (
                    (oldest[0][1] + policy.window_seconds - now)
                    if oldest
                    else policy.window_seconds
                )
                # Remove the just-added entry since we're rejecting
                await redis.zrem(key, str(now))
                raise RateLimitExceeded(
                    subject=subject,
                    retry_after_seconds=math.ceil(retry_after),
                )
        except RateLimitExceeded:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("Redis rate-limit check failed (%s); allowing request", exc)
