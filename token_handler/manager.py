"""
TokenManager — API key management for all AI providers.

Keys are stored in-memory only and never written to disk or logs.
Provides normalisation, validation, and retrieval with aliases.

Usage:
    mgr = TokenManager()
    mgr.set("anthropic", "sk-ant-...")
    key = mgr.get("claude")   # alias lookup
    ok  = mgr.validate("claude")
"""

import logging
import re
import time
from typing import Optional

log = logging.getLogger("token_handler.manager")

# Provider aliases — maps any alias to canonical provider name
_ALIASES: dict[str, str] = {
    "anthropic": "claude",
    "claude": "claude",
    "openai": "gpt",
    "gpt": "gpt",
    "gpt-4": "gpt",
    "xai": "grok",
    "grok": "grok",
    "x.ai": "grok",
    "copilot": "copilot",
    "github": "copilot",
    "ghp": "copilot",
    "gemini": "gemini",
    "google": "gemini",
    "cohere": "cohere",
    "mistral": "mistral",
    "perplexity": "perplexity",
}

# Prefix-based auto-detection
_PREFIX_MAP: list[tuple[str, str]] = [
    ("sk-ant-", "claude"),
    ("sk-proj-", "gpt"),
    ("sk-", "gpt"),
    ("xai-", "grok"),
    ("ghp_", "copilot"),
    ("AIza", "gemini"),
]

# Basic format validators (regex)
_VALIDATORS: dict[str, re.Pattern] = {
    "claude":   re.compile(r"^sk-ant-[A-Za-z0-9_\-]{20,}$"),
    "gpt":      re.compile(r"^sk-[A-Za-z0-9_\-]{20,}$"),
    "grok":     re.compile(r"^xai-[A-Za-z0-9_\-]{20,}$"),
    "copilot":  re.compile(r"^(ghp_|ghu_)[A-Za-z0-9]{20,}$"),
    "gemini":   re.compile(r"^AIza[A-Za-z0-9_\-]{30,}$"),
}


def _canonical(provider: str) -> str:
    """Resolve a provider name or alias to its canonical form."""
    return _ALIASES.get(provider.lower().strip(), provider.lower().strip())


def _detect_provider(key: str) -> Optional[str]:
    """Detect provider from key prefix."""
    for prefix, provider in _PREFIX_MAP:
        if key.startswith(prefix):
            return provider
    return None


class TokenManager:
    """In-memory API key store with provider normalisation and validation."""

    def __init__(self) -> None:
        # Stores: {canonical_provider: {"key": str, "added": int, "valid": bool}}
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def set(self, provider: str, key: str) -> str:
        """
        Store an API key. Auto-detects provider from key prefix if
        `provider` is ambiguous. Returns the canonical provider name.
        """
        key = key.strip()
        if not key:
            raise ValueError("API key cannot be empty")

        detected = _detect_provider(key)
        canonical = detected or _canonical(provider)

        valid = self.validate_key(canonical, key)
        self._store[canonical] = {
            "key": key,
            "added": int(time.time()),
            "valid": valid,
            "provider": canonical,
        }
        log.info("Key set for provider=%s valid=%s", canonical, valid)
        return canonical

    def get(self, provider: str) -> Optional[str]:
        """Retrieve a key by provider name or alias. Returns None if not set."""
        canonical = _canonical(provider)
        entry = self._store.get(canonical)
        return entry["key"] if entry else None

    def delete(self, provider: str) -> bool:
        """Remove a key. Returns True if it existed."""
        canonical = _canonical(provider)
        existed = canonical in self._store
        self._store.pop(canonical, None)
        if existed:
            log.info("Key removed for provider=%s", canonical)
        return existed

    def has(self, provider: str) -> bool:
        """Check whether a key is set for a provider."""
        return self.get(provider) is not None

    def providers(self) -> list[str]:
        """List all canonical providers that have a key set."""
        return list(self._store.keys())

    def status(self) -> dict[str, dict]:
        """Return sanitised status for all stored providers (no keys)."""
        return {
            k: {"valid": v["valid"], "added": v["added"]}
            for k, v in self._store.items()
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_key(self, provider: str, key: str) -> bool:
        """
        Validate an API key against known prefix/format patterns.
        Returns True for unknown providers (can't validate).
        """
        canonical = _canonical(provider)
        pattern = _VALIDATORS.get(canonical)
        if pattern is None:
            return True  # Unknown provider — assume valid
        return bool(pattern.match(key))

    def validate(self, provider: str) -> bool:
        """Validate the currently stored key for `provider`."""
        key = self.get(provider)
        if key is None:
            return False
        return self.validate_key(provider, key)

    # ------------------------------------------------------------------
    # Header helpers (for HTTP clients)
    # ------------------------------------------------------------------

    def auth_headers(self, provider: str) -> dict[str, str]:
        """Return the correct Authorization header for a provider."""
        key = self.get(provider)
        if not key:
            raise KeyError(f"No key stored for provider: {provider}")

        canonical = _canonical(provider)
        if canonical == "claude":
            return {"x-api-key": key, "anthropic-version": "2023-06-01"}
        elif canonical == "gpt":
            return {"Authorization": f"Bearer {key}"}
        elif canonical == "grok":
            return {"Authorization": f"Bearer {key}"}
        elif canonical == "copilot":
            return {"Authorization": f"Bearer {key}"}
        elif canonical == "gemini":
            return {}  # Gemini uses URL param; key embedded by caller
        else:
            return {"Authorization": f"Bearer {key}"}

    # ------------------------------------------------------------------
    # Import / export (metadata only)
    # ------------------------------------------------------------------

    def export_meta(self) -> dict[str, dict]:
        """Export provider metadata (no keys) — safe to log/send."""
        return self.status()

    def import_from_env(self, env: dict[str, str]) -> list[str]:
        """
        Bulk-import from an env dict (e.g. os.environ).
        Looks for *_API_KEY patterns. Returns list of providers set.
        """
        mapping = {
            "ANTHROPIC_API_KEY": "claude",
            "CLAUDE_API_KEY": "claude",
            "OPENAI_API_KEY": "gpt",
            "XAI_API_KEY": "grok",
            "GROK_API_KEY": "grok",
            "GITHUB_TOKEN": "copilot",
            "COPILOT_API_KEY": "copilot",
            "GEMINI_API_KEY": "gemini",
            "COHERE_API_KEY": "cohere",
            "MISTRAL_API_KEY": "mistral",
            "PERPLEXITY_API_KEY": "perplexity",
        }
        loaded: list[str] = []
        for env_key, provider in mapping.items():
            value = env.get(env_key, "").strip()
            if value:
                self.set(provider, value)
                loaded.append(provider)
        return loaded
