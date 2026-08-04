"""Local-first loopback dashboard server for Sovereignty AI Studio.

Binds exclusively to 127.0.0.1.  Surfaces repository status, agent status,
CI/CD workflow availability, local OAuth/CI/M4 status, and network-request
audit to the SGHv119 dashboard.  No shell access is exposed through any
endpoint; git is queried with bounded, hardcoded subprocess arguments and
no user-controlled input.

SOC 2-aligned controls: loopback-only binding, per-request audit log, explicit
CORS restriction to loopback origins.  This module does not make a SOC 2
certification claim.
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import pathlib
import subprocess
import threading
import time
from typing import Any

_LOG = logging.getLogger(__name__)

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
_ALLOWED_ORIGINS = frozenset(
    {
        "http://127.0.0.1:9898",
        "http://localhost:9898",
        "http://127.0.0.1",
        "http://localhost",
    }
)

# ---------------------------------------------------------------------------
# In-process audit ring-buffer (max 200 entries) populated by every request.
# ---------------------------------------------------------------------------

_audit_log: list[dict[str, Any]] = []
_audit_lock = threading.Lock()


def _record_audit(event: str, detail: str) -> None:
    entry: dict[str, Any] = {"event": event, "detail": detail, "ts": time.time()}
    with _audit_lock:
        _audit_log.append(entry)
        if len(_audit_log) > 200:
            _audit_log.pop(0)


# ---------------------------------------------------------------------------
# Read-only Git helpers — no user-controlled input, shell=False (default).
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: pathlib.Path = _REPO_ROOT) -> str:
    """Run a bounded, read-only git command with hardcoded arguments only."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


# ---------------------------------------------------------------------------
# Endpoint data builders
# ---------------------------------------------------------------------------


def _repo_status() -> dict[str, Any]:
    """Return branch, commit, and working-tree change counts."""
    branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    commit_full = _git("log", "--format=%H", "-1")
    commit = commit_full[:16] if commit_full else "unknown"
    porcelain = _git("status", "--porcelain")

    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []
    for line in porcelain.splitlines():
        if len(line) < 2:
            continue
        xy = line[:2]
        path_part = line[3:]
        if xy[0] not in (" ", "?", "!"):
            staged.append(path_part)
        if xy[1] not in (" ", "?", "!"):
            unstaged.append(path_part)
        if xy == "??":
            untracked.append(path_part)

    return {
        "branch": branch,
        "commit": commit,
        "staged_count": len(staged),
        "unstaged_count": len(unstaged),
        "untracked_count": len(untracked),
        "clean": not (staged or unstaged or untracked),
        "shell_access": "disabled",
    }


def _agent_status() -> dict[str, Any]:
    """Return agent module inventory from a local directory scan — no shell."""
    agents_dir = _REPO_ROOT / "agents"
    agent_files: list[str] = []
    if agents_dir.is_dir():
        agent_files = sorted(
            p.name
            for p in agents_dir.glob("*.py")
            if p.name != "__init__.py"
        )
    return {
        "agent_modules": agent_files,
        "count": len(agent_files),
        "source": "local-file-scan",
    }


def _cicd_status() -> dict[str, Any]:
    """Return CI/CD workflow availability from the local workflows directory."""
    wf_dir = _REPO_ROOT / "workflows"
    workflows: list[dict[str, str]] = []
    if wf_dir.is_dir():
        for p in sorted(wf_dir.glob("*.yml")):
            workflows.append({"name": p.stem, "file": p.name})
    gh_dir = _REPO_ROOT / ".github" / "workflows"
    if gh_dir.is_dir():
        for p in sorted(gh_dir.glob("*.yml")):
            workflows.append({"name": p.stem, "file": f".github/workflows/{p.name}"})
    return {
        "workflows": workflows,
        "count": len(workflows),
        "source": "local-workflow-scan",
    }


def _network_audit() -> dict[str, Any]:
    """Return the last 50 entries from the in-process audit ring-buffer."""
    with _audit_lock:
        entries = list(_audit_log[-50:])
    return {"entries": entries, "total": len(_audit_log)}


def _local_status() -> dict[str, Any]:
    """Offline OAuth / local-CI / M4 contract status. Fail-closed if module missing."""
    try:
        from bridge.local_dashboard_status import local_status  # type: ignore

        return local_status()
    except Exception:
        try:
            from local_dashboard_status import local_status  # type: ignore

            return local_status()
        except Exception as exc:  # noqa: BLE001
            return {
                "mode": "offline",
                "network_access": False,
                "error": "local_dashboard_status_unavailable",
                "detail": str(exc),
                "m4_neural": {"available": False, "tops": 38, "memory": "unified"},
            }


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------


class _DashboardHandler(http.server.BaseHTTPRequestHandler):
    """Loopback-only HTTP handler for dashboard REST endpoints."""

    _CORS_COMMON = {
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Vary": "Origin",
    }

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D102
        _LOG.debug(fmt, *args)

    def _is_loopback(self) -> bool:
        peer = self.client_address[0]
        host = self.headers.get("Host", "").split(":")[0]
        return peer in _LOOPBACK_HOSTS or host in _LOOPBACK_HOSTS

    def _send_json(self, code: int, body: dict[str, Any]) -> None:
        data = json.dumps(body, default=str).encode()
        origin = self.headers.get("Origin", "")
        cors_origin = origin if origin in _ALLOWED_ORIGINS else "http://127.0.0.1:9898"
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", cors_origin)
        for key, value in self._CORS_COMMON.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        origin = self.headers.get("Origin", "")
        cors_origin = origin if origin in _ALLOWED_ORIGINS else "http://127.0.0.1:9898"
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", cors_origin)
        for key, value in self._CORS_COMMON.items():
            self.send_header(key, value)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if not self._is_loopback():
            _record_audit("BLOCKED_NON_LOOPBACK", self.client_address[0])
            self._send_json(403, {"error": "Loopback access only"})
            return

        path = self.path.split("?")[0]
        _record_audit("REQUEST", path)

        routes: dict[str, Any] = {
            "/api/repo-status": _repo_status,
            "/api/agent-status": _agent_status,
            "/api/cicd-status": _cicd_status,
            "/api/network-audit": _network_audit,
            "/api/local-status": _local_status,
            "/health": lambda: {"status": "ok", "service": "dashboard-server"},
            "/api/health": lambda: {"status": "ok", "service": "dashboard-server"},
        }
        handler = routes.get(path)
        if handler is None:
            self._send_json(404, {"error": "Not found", "path": path})
            return
        try:
            self._send_json(200, handler())
        except Exception as exc:  # noqa: BLE001
            _LOG.error("Handler error for %s: %s", path, exc)
            self._send_json(500, {"error": "Internal server error"})


# ---------------------------------------------------------------------------
# Server class
# ---------------------------------------------------------------------------


class DashboardServer:
    """Loopback-only HTTP server that exposes local dashboard endpoints.

    The server unconditionally refuses to bind to any address outside the
    loopback range, preventing accidental exposure on LAN or public interfaces.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9898) -> None:
        if host not in _LOOPBACK_HOSTS:
            raise ValueError(
                f"DashboardServer must bind to a loopback address, got {host!r}"
            )
        self.host = host
        self.port = port
        self._server: http.server.HTTPServer | None = None

    def start(self) -> None:
        """Start serving (blocks until stop() is called or interrupted)."""
        self._server = http.server.HTTPServer((self.host, self.port), _DashboardHandler)
        _LOG.info(
            "Dashboard server listening on %s:%s (loopback only)", self.host, self.port
        )
        self._server.serve_forever()

    def stop(self) -> None:
        """Shut down the server cleanly."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None

    @staticmethod
    def record_audit(event: str, detail: str) -> None:
        """Expose audit recording to external callers (e.g., the bridge)."""
        _record_audit(event, detail)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    port = int(os.environ.get("SG_DASHBOARD_PORT", "9898"))
    srv = DashboardServer(port=port)
    try:
        srv.start()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
