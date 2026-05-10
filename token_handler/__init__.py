"""
Sovereignty AI Studio — Token Handler Module

Manages API tokens and session tokens:
  - Secure in-memory key store for provider API keys (never persisted to disk)
  - Provider normalisation (anthropic→claude, openai→gpt, xai→grok)
  - Token validation (format checks per provider)
  - Session token generation / rotation
  - JWT lifecycle: issue, validate, refresh, revoke (token_manager)
  - Per-token / per-user sliding-window rate limiting (rate_limiter)

Exports:
    TokenManager        — provider API key store (manager.py)
    SessionTokenManager — session token lifecycle (session.py)
    JWTTokenManager     — JWT issue/validate/refresh/revoke (token_manager.py)
    RateLimiter         — sliding-window rate limiter (rate_limiter.py)
"""

from .manager import TokenManager
from .session import SessionTokenManager
from .token_manager import TokenManager as JWTTokenManager, TokenClaims, TokenError
from .rate_limiter import RateLimiter, RateLimitExceeded

__all__ = [
    "TokenManager",
    "SessionTokenManager",
    "JWTTokenManager",
    "TokenClaims",
    "TokenError",
    "RateLimiter",
    "RateLimitExceeded",
]
