#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REMOTE_URL = "https://github.com/Sovereignty-One/SuperGrok-Heavy-4-2-Skeleton.git"
DEFAULT_DEST = REPO_ROOT / "external" / "SuperGrok-Heavy-4-2-Skeleton"
STATE_FILE = REPO_ROOT / ".sync_state" / "supergrok-heavy-4-2-skeleton.json"

# Each tuple is (pattern, replacement).  Patterns that capture a leading key +
# optional quote must use \1\2 so the quote is re-emitted in the replacement.
_REDACTED = "***REDACTED***"

SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # unquoted or quoted assignment:  api_key = VALUE  /  api_key: VALUE
    (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([\"'])[A-Za-z0-9_\-]{12,}\2"), r"\1\2" + _REDACTED + r"\2"),
    (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([A-Za-z0-9_\-]{12,})"), r"\1" + _REDACTED),
    (re.compile(r"(?i)(token\s*[=:]\s*)([\"'])[A-Za-z0-9_\-]{12,}\2"), r"\1\2" + _REDACTED + r"\2"),
    (re.compile(r"(?i)(token\s*[=:]\s*)([A-Za-z0-9_\-]{12,})"), r"\1" + _REDACTED),
    (re.compile(r"(?i)(secret\s*[=:]\s*)([\"'])[^\s\"']{8,}\2"), r"\1\2" + _REDACTED + r"\2"),
    (re.compile(r"(?i)(secret\s*[=:]\s*)([^\s\"']{8,})"), r"\1" + _REDACTED),
    # JSON / dict style:  "api_key": "VALUE"  or  "token":"VALUE"
    (re.compile(r'(?i)("(?:api[_-]?key|token|secret|password|passwd|private_?key)"\s*:\s*")([^"]{8,})(")'), r"\1" + _REDACTED + r"\3"),
    (re.compile(r"(?i)('(?:api[_-]?key|token|secret|password|passwd|private_?key)'\s*:\s*')([^']{8,})(')"), r"\1" + _REDACTED + r"\3"),
    # Bearer / Authorization headers
    (re.compile(r"(?i)(Authorization\s*:\s*(?:Bearer|Token)\s+)([A-Za-z0-9_\-\.]{12,})"), r"\1" + _REDACTED),
    # JWT (three base64url segments)
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), _REDACTED),
)


@dataclass(frozen=True)
class Change:
    status: str
    path: str
    old_path: str | None = None


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=True,
    )
    return proc.stdout


def _safe_rel_path(rel_path: str) -> Path:
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe path from remote repo: {rel_path}")
    return rel


def _sanitize_text(text: str) -> str:
    sanitized = text
    for pattern, repl in SECRET_PATTERNS:
        sanitized = pattern.sub(repl, sanitized)
    return sanitized


# UTF-16/UTF-32 BOMs (files that are text but contain NUL bytes).
_TEXT_BOMS = (
    b"\xff\xfe\x00\x00",  # UTF-32 LE
    b"\x00\x00\xfe\xff",  # UTF-32 BE
    b"\xff\xfe",           # UTF-16 LE
    b"\xfe\xff",           # UTF-16 BE
)


def _is_binary(data: bytes) -> bool:
    """Return True only for truly binary data (not Unicode text with NUL bytes)."""
    # Allow UTF-16/UTF-32 BOM-prefixed files to be treated as text.
    for bom in _TEXT_BOMS:
        if data.startswith(bom):
            return False
    return b"\x00" in data


def _list_changes(repo_dir: Path, branch_ref: str, since: datetime) -> list[Change]:
    out = _run(
        [
            "git",
            "log",
            branch_ref,
            f"--since={since.isoformat()}",
            "--name-status",
            "--pretty=format:",
        ],
        cwd=repo_dir,
    )

    latest_by_path: OrderedDict[str, Change] = OrderedDict()
    for raw in out.splitlines():
        line = raw.strip()
        if not line:
            continue

        parts = line.split("\t")
        status = parts[0]
        kind = status[0]

        if kind in {"A", "M", "D"} and len(parts) >= 2:
            rel = parts[1]
            if rel not in latest_by_path:
                latest_by_path[rel] = Change(status=kind, path=rel)
        elif kind == "R" and len(parts) >= 3:
            old_path, new_path = parts[1], parts[2]
            if old_path not in latest_by_path:
                latest_by_path[old_path] = Change(status="D", path=old_path)
            if new_path not in latest_by_path:
                latest_by_path[new_path] = Change(status="A", path=new_path, old_path=old_path)

    return list(latest_by_path.values())


def _read_remote_file(repo_dir: Path, branch_ref: str, rel_path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{branch_ref}:{rel_path}"],
        cwd=str(repo_dir),
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to read remote file: {rel_path}\n{proc.stderr.decode(errors='replace')}")
    return proc.stdout


def _count_duplicate_hashes(root: Path) -> tuple[int, int]:
    if not root.exists():
        return (0, 0)

    seen: dict[str, Path] = {}
    duplicates = 0
    checked = 0
    for file in sorted(p for p in root.rglob("*") if p.is_file()):
        checked += 1
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest not in seen:
            seen[digest] = file
            continue

        duplicates += 1
    return checked, duplicates


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _prepare_remote(remote_url: str, branch: str) -> tuple[Path, str]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="sg-heavy-sync-"))
    _run(["git", "init", "-q"], cwd=tmp_dir)
    _run(["git", "remote", "add", "origin", remote_url], cwd=tmp_dir)
    _run(["git", "fetch", "--prune", "origin", branch], cwd=tmp_dir)
    return tmp_dir, f"origin/{branch}"


def sync_changes(*, remote_url: str, branch: str, dest_dir: Path, days: int, dry_run: bool = False) -> dict:
    remote_dir, branch_ref = _prepare_remote(remote_url, branch)
    state = _load_state()

    # Use the last recorded sync timestamp if available; otherwise fall back to
    # the caller-supplied window so the first run still gets a reasonable slice.
    last_sync_raw = state.get("last_sync_utc")
    if last_sync_raw:
        try:
            since = datetime.fromisoformat(last_sync_raw)
        except ValueError:
            since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    else:
        since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    try:
        changes = _list_changes(remote_dir, branch_ref, since)
        copied = 0
        deleted = 0

        for change in changes:
            rel = _safe_rel_path(change.path)
            target = dest_dir / rel

            if change.status == "D":
                if target.exists():
                    deleted += 1
                    if not dry_run:
                        if target.is_dir():
                            shutil.rmtree(target)
                        else:
                            target.unlink()
                continue

            if change.status not in {"A", "M"}:
                continue

            payload = _read_remote_file(remote_dir, branch_ref, change.path)

            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                # Remove any conflicting filesystem entry (e.g. a directory where
                # the remote now has a file, or vice-versa).
                if target.exists() or target.is_symlink():
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target)
                    else:
                        target.unlink()

            if _is_binary(payload):
                if not dry_run:
                    target.write_bytes(payload)
            else:
                text = payload.decode("utf-8", errors="surrogateescape")
                sanitized = _sanitize_text(text)
                if not dry_run:
                    target.write_text(sanitized, encoding="utf-8", errors="surrogateescape")
            copied += 1

        checked = duplicates = 0
        if not dry_run:
            checked, duplicates = _count_duplicate_hashes(dest_dir)

            state.update(
                {
                    "remote_url": remote_url,
                    "branch": branch,
                    "last_sync_utc": datetime.now(tz=timezone.utc).isoformat(),
                    "window_days": days,
                }
            )
            _save_state(state)

        return {
            "copied_or_updated": copied,
            "deleted": deleted,
            "dedupe_checked": checked,
            "dedupe_detected": duplicates,
            "changes_detected": len(changes),
            "dry_run": dry_run,
        }
    finally:
        shutil.rmtree(remote_dir, ignore_errors=True)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync recent updates from SuperGrok-Heavy-4-2-Skeleton.")
    parser.add_argument("--remote-url", default=DEFAULT_REMOTE_URL)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--dest", default=str(DEFAULT_DEST))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def main() -> int:
    args = parse_args()
    dest = Path(args.dest)
    summary = sync_changes(
        remote_url=args.remote_url,
        branch=args.branch,
        dest_dir=dest,
        days=max(1, args.days),
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
