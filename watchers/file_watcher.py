"""
watchers/file_watcher.py
=========================
Watches config and model files for on-disk changes and triggers hot-reload
callbacks — no file-system event library required (polling-based, stdlib only).

How it works
------------
A background asyncio task polls each watched file's ``mtime`` and ``size``
every *poll_interval* seconds.  When a change is detected it emits a
:class:`FileChangeEvent` and calls all registered callbacks.

Usage::

    watcher = FileWatcher(["config.json", "models/"])
    watcher.on_change(lambda event: print(f"Changed: {event.path}"))
    await watcher.start()
    # ... later ...
    await watcher.stop()
"""

from __future__ import annotations

import asyncio
import logging
import os
import pathlib
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set

log = logging.getLogger(__name__)

# Default polling interval in seconds
_DEFAULT_POLL_INTERVAL: float = 2.0


@dataclass
class FileChangeEvent:
    """Describes a detected file-system change.

    Attributes:
        path:       Absolute path that changed.
        old_mtime:  ``mtime`` before the change (0.0 if file is new).
        new_mtime:  ``mtime`` after the change.
        old_size:   File size in bytes before the change.
        new_size:   File size in bytes after the change.
        kind:       ``"created"``, ``"modified"``, or ``"deleted"``.
    """

    path: str
    old_mtime: float
    new_mtime: float
    old_size: int
    new_size: int
    kind: str  # "created" | "modified" | "deleted"


# Type alias for change callbacks
FileChangeCallback = Callable[[FileChangeEvent], None]


@dataclass
class _FileState:
    """Internal snapshot of a file's state at the last poll."""

    mtime: float = 0.0
    size: int = 0
    exists: bool = False


class FileWatcher:
    """Polls a set of files/directories for changes and fires callbacks.

    Args:
        paths:         File or directory paths to monitor.  Directories are
                       monitored non-recursively (immediate children only).
        poll_interval: Seconds between polls.  Lower values are more responsive
                       but consume more CPU.  Default: 2 s.

    Example::

        watcher = FileWatcher(paths=["config.json", ".env"])

        @watcher.on_change
        def reload_config(event: FileChangeEvent):
            if event.kind in ("created", "modified"):
                load_config(event.path)

        await watcher.start()
    """

    def __init__(
        self,
        paths: Optional[List[str]] = None,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
    ) -> None:
        self._paths: List[str] = list(paths or [])
        self.poll_interval = poll_interval
        self._callbacks: List[FileChangeCallback] = []
        self._states: Dict[str, _FileState] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_path(self, path: str) -> None:
        """Add a file or directory to the watch list at runtime."""
        if path not in self._paths:
            self._paths.append(path)
            log.debug("FileWatcher: added path '%s'", path)

    def on_change(self, callback: FileChangeCallback) -> FileChangeCallback:
        """Register a callback to be called on every file change.

        Can be used as a decorator::

            @watcher.on_change
            def handler(event): ...

        Or called directly::

            watcher.on_change(my_handler)

        Returns the callback unchanged so decorator usage works.
        """
        self._callbacks.append(callback)
        return callback

    async def start(self) -> None:
        """Begin polling in a background asyncio task."""
        if self._running:
            return
        self._running = True
        # Capture initial state so first poll does not produce false alarms
        self._snapshot_all()
        self._task = asyncio.create_task(self._poll_loop(), name="file_watcher")
        log.info(
            "FileWatcher started: watching %d path(s) every %.1fs",
            len(self._paths),
            self.poll_interval,
        )

    async def stop(self) -> None:
        """Stop the background polling task gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("FileWatcher stopped.")

    # ------------------------------------------------------------------
    # Internal polling loop
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Background loop: poll every *poll_interval* seconds."""
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
                self._check_all()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                log.warning("FileWatcher poll error: %s", exc)

    def _check_all(self) -> None:
        """Check all watched paths for changes."""
        expanded = self._expand_paths()
        for path in expanded:
            self._check_path(path)

    def _expand_paths(self) -> Set[str]:
        """Expand directories to their immediate children."""
        result: Set[str] = set()
        for p in self._paths:
            path = pathlib.Path(p)
            if path.is_dir():
                for child in path.iterdir():
                    if child.is_file():
                        result.add(str(child))
            else:
                result.add(str(path))
        return result

    def _check_path(self, path: str) -> None:
        """Compare current file state against the last snapshot, emit events."""
        prev = self._states.get(path, _FileState())
        current = _FileState()

        try:
            stat = os.stat(path)
            current.mtime = stat.st_mtime
            current.size = stat.st_size
            current.exists = True
        except FileNotFoundError:
            current.exists = False

        if not prev.exists and not current.exists:
            # File never existed and still doesn't — nothing to report
            return

        if not prev.exists and current.exists:
            kind = "created"
        elif prev.exists and not current.exists:
            kind = "deleted"
        elif current.mtime != prev.mtime or current.size != prev.size:
            kind = "modified"
        else:
            # No change
            self._states[path] = current
            return

        self._states[path] = current
        event = FileChangeEvent(
            path=path,
            old_mtime=prev.mtime,
            new_mtime=current.mtime,
            old_size=prev.size,
            new_size=current.size,
            kind=kind,
        )
        log.info("FileWatcher: %s → %s", kind.upper(), path)
        self._emit(event)

    def _emit(self, event: FileChangeEvent) -> None:
        """Call all registered callbacks with *event*."""
        for cb in self._callbacks:
            try:
                result = cb(event)
                # Support both sync and async callbacks
                if asyncio.iscoroutine(result):
                    asyncio.ensure_future(result)
            except Exception as exc:  # noqa: BLE001
                log.warning("FileWatcher callback error: %s", exc)

    def _snapshot_all(self) -> None:
        """Take an initial snapshot so the first poll does not raise false alarms."""
        for path in self._expand_paths():
            state = _FileState()
            try:
                stat = os.stat(path)
                state.mtime = stat.st_mtime
                state.size = stat.st_size
                state.exists = True
            except FileNotFoundError:
                pass
            self._states[path] = state
