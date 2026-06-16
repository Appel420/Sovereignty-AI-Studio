"""Utility functions for tracking file access."""

import builtins
        fix/pylint-ci-2
import contextlib
import datetime

        main
import os

FILE_LOG = "/system/scar/file-access.log"
_ORIG_OPEN = builtins.open
_ORIG_WRITE = os.write


def mark_open(path: str, action: str = "open"):
    """Log a file touch."""
    entry = f"Ara | {action}: '{path}'\n"
    try:
        with _ORIG_OPEN(FILE_LOG, "a", encoding="utf-8") as file_handle:
            file_handle.write(entry)
    except OSError:
        pass


def safe_open(*args, action="open", **kwargs):
    """Wrapper that logs file access before opening."""
    path = args[0] if args else kwargs.get("file", kwargs.get("path"))
    mark_open(path, action)
        fix/pylint-ci-2
    file_handle = _ORIG_OPEN(*args, **kwargs)
    try:
        yield file_handle
    finally:
        try:
            file_handle.close()
        except OSError:
            pass

    return _ORIG_OPEN(*args, **kwargs)
        main


def safe_write(fd, data):
    """Log write access for os.write calls."""
    path = getattr(fd, "name", None)
    if path is None and isinstance(fd, int):
        try:
            path = os.readlink(f"/proc/self/fd/{fd}")
        except Exception:
            path = "unknown"
    mark_open(path or "unknown", "write")
    return _ORIG_WRITE(fd, data)


file_open = safe_open
os.write = safe_write
