"""Utility functions for tracking file access."""

import contextlib
import datetime
import os
import builtins

FILE_LOG = "/system/scar/file-access.log"
_ORIG_OPEN = builtins.open
_ORIG_WRITE = os.write


def mark_open(path: str, action: str = "open"):
    """Log a file touch."""
    entry = f"Ara | {action}: '{path}'\n"
    try:
        with _ORIG_OPEN(FILE_LOG, "a", encoding="utf-8") as file_handle:
            file_handle.write(entry)
    except Exception:
        pass


@contextlib.contextmanager
def safe_file(*args, **kwargs):
    """Context manager that logs file access before opening."""
    path = args[0] if args else kwargs.get("path")
    action = kwargs.get("action", "open")
    mark_open(path, action)
    file_handle = _ORIG_OPEN(*args, **kwargs)
    try:
        yield file_handle
    finally:
        try:
            file_handle.close()
        except Exception as exc:
            print(f"Error closing file {path}: {exc}")


def safe_write(fd, data):
    """Log write access for os.write calls."""
    if isinstance(data, str):
        path = getattr(fd, "name", "unknown")
        mark_open(path, "write")
    return _ORIG_WRITE(fd, data)


open = safe_file
os.write = safe_write
