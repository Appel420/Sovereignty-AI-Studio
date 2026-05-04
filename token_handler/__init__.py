"""
Sovereignty AI Studio — Token Handler
======================================
Centralised JWT / API-token management with rotation, expiry, and refresh.

Exports:
    TokenManager  — issue, validate, refresh, and revoke JWT tokens
    RateLimiter   — per-token / per-user sliding-window rate limiting

Typical usage::

    from token_handler import TokenManager, RateLimiter

    tm = TokenManager()
    token = tm.issue(subject="user:alice", scopes=["read", "write"])

    rl = RateLimiter()
    allowed = await rl.check("user:alice")
"""

from .token_manager import TokenManager, TokenClaims, TokenError
from .rate_limiter import RateLimiter, RateLimitExceeded

__all__ = [
    "TokenManager",
    "TokenClaims",
    "TokenError",
    "RateLimiter",
    "RateLimitExceeded",
]
