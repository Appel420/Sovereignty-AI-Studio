"""
Sovereignty AI Studio — Common Helper Utilities.

Re-usable utility functions consumed by multiple modules.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, Iterable, List, Optional, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Dict helpers
# ---------------------------------------------------------------------------

def safe_get(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Navigate nested dicts safely, returning *default* on any missing key."""
    current: Any = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge an arbitrary number of dicts (later dicts take precedence)."""
    result: Dict[str, Any] = {}
    for d in dicts:
        for k, v in d.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = merge_dicts(result[k], v)
            else:
                result[k] = v
    return result


def pick(d: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    """Return a new dict containing only the keys in *keys* that exist in *d*."""
    return {k: d[k] for k in keys if k in d}


def omit(d: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    """Return a new dict with the given *keys* removed."""
    exclude = set(keys)
    return {k: v for k, v in d.items() if k not in exclude}


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------

def sha3_512_hex(data: str) -> str:
    """Return the SHA3-512 hex digest of *data*."""
    return hashlib.sha3_512(data.encode()).hexdigest()


def sha256_hex(data: str) -> str:
    """Return the SHA-256 hex digest of *data*."""
    return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

class Timer:
    """Context-manager based wall-clock timer."""

    def __init__(self, name: str = "") -> None:
        self.name = name
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *_: Any) -> None:
        self.elapsed_ms = (time.monotonic() - self._start) * 1000.0
        if self.name:
            log.debug("⏱ %s took %.1f ms", self.name, self.elapsed_ms)


# ---------------------------------------------------------------------------
# Collection helpers
# ---------------------------------------------------------------------------

def chunk(lst: List[T], size: int) -> List[List[T]]:
    """Split *lst* into sub-lists of at most *size* elements."""
    if size <= 0:
        raise ValueError("chunk size must be a positive integer")
    return [lst[i: i + size] for i in range(0, len(lst), size)]


def flatten(nested: Iterable[Iterable[T]]) -> List[T]:
    """Flatten one level of nesting from *nested*."""
    return [item for sublist in nested for item in sublist]


def first(iterable: Iterable[T], default: Optional[T] = None) -> Optional[T]:
    """Return the first element of *iterable*, or *default* if empty."""
    return next(iter(iterable), default)


def unique(lst: List[T]) -> List[T]:
    """Return *lst* with duplicates removed, preserving order."""
    seen: set = set()
    result: List[T] = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def truncate(text: str, max_len: int = 200, ellipsis: str = "…") -> str:
    """Truncate *text* to *max_len* characters, appending *ellipsis* if cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(ellipsis)] + ellipsis


def sanitize_key(key: str) -> str:
    """Normalise a dict key: strip, lowercase, replace spaces/hyphens with underscores."""
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def coerce_bool(value: Any) -> bool:
    """
    Coerce common truthy string representations to bool.

    Accepts ``True``, ``"true"``, ``"1"``, ``"yes"``, ``"on"`` (case-insensitive).
    Anything else returns ``False``.
    """
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}
