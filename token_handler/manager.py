"""
TokenManager — API key management for all AI providers.

Keys are stored in-memory and optionally persisted to an encrypted local file
(.sg_token_store) so that user-entered keys survive bridge restarts.
Encryption uses ChaCha20-Poly1305 with a per-install key stored in
.sg_token_key (chmod 0600).  If the `cryptography` package is unavailable
the manager falls back to in-memory-only mode gracefully.

Usage:
    mgr = TokenManager()
    mgr.set("anthropic", "sk-ant-...")
    key = mgr.get("claude")   # alias lookup
    ok  = mgr.validate("claude")
"""

import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("token_handler.manager")

# ---------------------------------------------------------------------------
# Encrypted persistence helpers
# ---------------------------------------------------------------------------

_TOKEN_KEY_FILE = Path(".sg_token_key")
_TOKEN_STORE_FILE = Path(".sg_token_store")

try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305 as _ChaCha
    import json as _json
    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False


def _get_or_create_token_key() -> bytes:
    """Return the 32-byte encryption key for the token store, creating it once."""
    if _TOKEN_KEY_FILE.exists():
        raw = _TOKEN_KEY_FILE.read_text(encoding="utf-8").strip()
        if raw:
            return bytes.fromhex(raw)
    key = os.urandom(32)
    _TOKEN_KEY_FILE.write_text(key.hex(), encoding="utf-8")
    try:
        os.chmod(_TOKEN_KEY_FILE, 0o600)
    except OSError:
        pass
    return key


def _persist_tokens(store: dict) -> None:
    """Encrypt and write *store* to .sg_token_store."""
    if not _CRYPTO_OK:
        return
    try:
        key = _get_or_create_token_key()
        aead = _ChaCha(key)
        nonce = os.urandom(12)
        plaintext = _json.dumps(store).encode()
        ciphertext = aead.encrypt(nonce, plaintext, None)
        _TOKEN_STORE_FILE.write_bytes(nonce + ciphertext)
        try:
            os.chmod(_TOKEN_STORE_FILE, 0o600)
        except OSError:
            pass
    except Exception as exc:
        log.debug("token_store persist error: %s", exc)


def _load_persisted_tokens() -> dict:
    """Decrypt and return stored tokens, or {} on any error."""
    if not _CRYPTO_OK or not _TOKEN_STORE_FILE.exists():
        return {}
    try:
        key = _get_or_create_token_key()
        raw = _TOKEN_STORE_FILE.read_bytes()
        if len(raw) < 13:
            return {}
        nonce, ciphertext = raw[:12], raw[12:]
        aead = _ChaCha(key)
        plaintext = aead.decrypt(nonce, ciphertext, None)
        return _json.loads(plaintext.decode())
    except Exception as exc:
        log.debug("token_store load error (returning empty): %s", exc)
        return {}

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
    """API key store with provider normalisation, validation, and encrypted persistence."""

    def __init__(self) -> None:
        # Restore keys that were persisted during a previous session.
        self._store: dict[str, dict] = _load_persisted_tokens()
        if self._store:
            log.info("Loaded %d persisted provider key(s) from store", len(self._store))

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
        _persist_tokens(self._store)
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
            _persist_tokens(self._store)
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
