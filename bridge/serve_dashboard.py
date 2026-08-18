"""Local-first loopback dashboard server for Sovereignty AI Studio."""
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
_ALLOWED_ORIGINS = frozenset({"http://127.0.0.1:9898", "http://localhost:9898", "http://127.0.0.1", "http://localhost"})
_audit_log: list[dict[str, Any]] = []
_audit_lock = threading.Lock()


def _record_audit(event: str, detail: str) -> None:
    with _audit_lock:
        _audit_log.append({"event": event, "detail": detail, "ts": time.time()})
        del _audit_log[:-200]


def _git(*args: str, cwd: pathlib.Path = _REPO_ROOT) -> str:
    try:
        result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=5, check=False)
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _repo_status() -> dict[str, Any]:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    commit = (_git("log", "--format=%H", "-1") or "unknown")[:16]
    porcelain = _git("status", "--porcelain")
    return {"branch": branch, "commit": commit, "changes": len(porcelain.splitlines()), "clean": not porcelain}


def _agent_status() -> dict[str, Any]:
    directory = _REPO_ROOT / "agents"
    files = sorted(p.name for p in directory.glob("*.py") if p.name != "__init__.py") if directory.is_dir() else []
    return {"agent_modules": files, "count": len(files), "source": "local-file-scan"}


def _cicd_status() -> dict[str, Any]:
    directory = _REPO_ROOT / ".github" / "workflows"
    files = sorted(p.name for p in directory.glob("*.yml")) if directory.is_dir() else []
    return {"workflows": files, "count": len(files), "source": "local-workflow-scan"}


def _network_audit() -> dict[str, Any]:
    with _audit_lock:
        return {"entries": list(_audit_log[-50:]), "total": len(_audit_log)}


def _local_status() -> dict[str, Any]:
    """Return the canonical offline/OAuth/M4 status payload."""
    from .local_dashboard_status import local_status
    return local_status()


class _DashboardHandler(http.server.BaseHTTPRequestHandler):
    _CORS_COMMON = {"Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Vary": "Origin"}

    def log_message(self, fmt: str, *args: object) -> None:
        _LOG.debug(fmt, *args)

    def _is_loopback(self) -> bool:
        return self.client_address[0] in _LOOPBACK_HOSTS or self.headers.get("Host", "").split(":")[0] in _LOOPBACK_HOSTS

    def _send_json(self, code: int, body: dict[str, Any]) -> None:
        data = json.dumps(body, default=str).encode()
        origin = self.headers.get("Origin", "")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", origin if origin in _ALLOWED_ORIGINS else "http://127.0.0.1:9898")
        for key, value in self._CORS_COMMON.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if not self._is_loopback():
            _record_audit("BLOCKED_NON_LOOPBACK", self.client_address[0])
            self._send_json(403, {"error": "Loopback access only"})
            return
        path = self.path.split("?")[0]
        _record_audit("REQUEST", path)
        routes = {
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


class DashboardServer:
    """Loopback-only HTTP server."""
    def __init__(self, host: str = "127.0.0.1", port: int = 9898) -> None:
        if host not in _LOOPBACK_HOSTS:
            raise ValueError(f"DashboardServer must bind to loopback, got {host!r}")
        self.host = host
        self.port = port
        self._server: http.server.HTTPServer | None = None

    def start(self) -> None:
        self._server = http.server.HTTPServer((self.host, self.port), _DashboardHandler)
        self._server.serve_forever()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None

    @staticmethod
    def record_audit(event: str, detail: str) -> None:
        _record_audit(event, detail)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    DashboardServer(port=int(os.environ.get("SG_DASHBOARD_PORT", "9898"))).start()


if __name__ == "__main__":
    main()
