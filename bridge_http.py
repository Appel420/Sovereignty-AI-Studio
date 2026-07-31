#!/usr/bin/env python3
"""HTTP companion for bridge.py — policy check, ledger undo/redo/history, health.

Binds to 127.0.0.1 only. Fail-closed when authority or ledger modules are absent.
Does not invent success. Full reasoning text never leaves the device.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("SG_HTTP_HOST", "127.0.0.1")
PORT = int(os.environ.get("SG_HTTP_PORT", "9896"))
ROOT = Path(__file__).resolve().parent


def _try_import_authority():
    try:
        from sia.authority import SovereignAuthority  # type: ignore
        from sia.audit.recorder import AuditRecorder  # type: ignore

        return SovereignAuthority, AuditRecorder
    except Exception:
        return None, None


def _try_import_undo():
    try:
        from sia.audit.undo_redo import UndoableLedger  # type: ignore
        from sia.audit.ledger import AuditLedger  # type: ignore

        return UndoableLedger, AuditLedger
    except Exception:
        return None, None


def load_state_policy() -> dict[str, Any]:
    """Default DEVICE_ONLY policy. Override via env SG_STATE_POLICY_JSON if present."""
    default = {
        "mode": "DEVICE_ONLY",
        "allow_external_memory": False,
        "allow_provider_training": False,
        "allow_cross_session_sync": False,
        "allow_telemetry": False,
    }
    raw = os.environ.get("SG_STATE_POLICY_JSON")
    if not raw:
        return default
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {**default, **data}
    except json.JSONDecodeError:
        pass
    return default


def policy_check(provider: str | None) -> dict[str, Any]:
    policy = load_state_policy()
    mode = str(policy.get("mode", "DEVICE_ONLY")).upper()
    blocked = []
    if mode in {"DEVICE_ONLY", "GHOST"} and provider:
        # Execution may still be local; external memory / training always denied in ghost.
        if policy.get("allow_external_memory") is True:
            blocked.append("external_memory_not_allowed_in_device_only")
        if policy.get("allow_provider_training") is True:
            blocked.append("provider_training_not_allowed_in_device_only")
    allowed = len(blocked) == 0
    return {
        "allowed": allowed,
        "mode": mode,
        "provider": provider or None,
        "state_policy": policy,
        "reason": "ok" if allowed else ";".join(blocked) or "policy_denied",
        "policy_file": "docs/DEVICE_STATE_SOVEREIGNTY_POLICY_v1.1.1.md",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "SovereigntyBridgeHTTP/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep quiet; use structured JSON responses instead of noisy access logs.
        return

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/health":
            self._json(
                200,
                {
                    "status": "healthy",
                    "service": "bridge-http",
                    "bind": f"{HOST}:{PORT}",
                    "mode": "device-local",
                    "policy": load_state_policy().get("mode"),
                    "ledger": "available" if _try_import_undo()[0] else "not_configured",
                    "authority": "available" if _try_import_authority()[0] else "not_configured",
                },
            )
            return

        if path == "/policy/check":
            provider = (qs.get("provider") or [None])[0]
            result = policy_check(provider)
            self._json(200 if result["allowed"] else 403, result)
            return

        if path == "/ledger/history":
            target = (qs.get("target") or [None])[0]
            UndoableLedger, AuditLedger = _try_import_undo()
            if not UndoableLedger or not AuditLedger:
                self._json(
                    503,
                    {
                        "error": "ledger_not_configured",
                        "detail": "sia.audit.undo_redo / AuditLedger not importable on this runtime",
                    },
                )
                return
            if not target:
                self._json(400, {"error": "target_required"})
                return
            try:
                ledger = AuditLedger()
                undo = UndoableLedger(ledger)
                history = [
                    {
                        "event_type": getattr(e, "event_type", None),
                        "payload": getattr(e, "payload", None),
                    }
                    for e in undo.history_for(target)
                ]
                self._json(200, {"target": target, "entries": history})
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"error": "ledger_history_failed", "detail": str(exc)})
            return

        self._json(404, {"error": "not_found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        body = self._read_json()

        if path in {"/ledger/undo", "/ledger/redo"}:
            UndoableLedger, AuditLedger = _try_import_undo()
            if not UndoableLedger or not AuditLedger:
                self._json(
                    503,
                    {
                        "error": "ledger_not_configured",
                        "detail": "UndoableLedger not available — install/wire sia.audit modules",
                    },
                )
                return
            entry_id = body.get("entry_id")
            actor_id = body.get("actor_id")
            if not isinstance(entry_id, int) or not isinstance(actor_id, str) or not actor_id:
                self._json(400, {"error": "entry_id (int) and actor_id (str) required"})
                return
            try:
                ledger = AuditLedger()
                undo = UndoableLedger(ledger)
                if path.endswith("undo"):
                    entry = undo.undo(entry_id, actor_id=actor_id)
                else:
                    entry = undo.redo(entry_id, actor_id=actor_id)
                self._json(
                    200,
                    {
                        "ok": True,
                        "event_type": getattr(entry, "event_type", None),
                        "actor_id": actor_id,
                        "entry_id": entry_id,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                self._json(400, {"error": "ledger_mutation_failed", "detail": str(exc)})
            return

        self._json(404, {"error": "not_found", "path": path})


def main() -> None:
    if HOST not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing non-loopback bind. Set SG_HTTP_HOST=127.0.0.1")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"bridge_http listening on http://{HOST}:{PORT}")
    print("  GET  /health")
    print("  GET  /policy/check?provider=<id>")
    print("  GET  /ledger/history?target=<id>")
    print("  POST /ledger/undo  {entry_id, actor_id}")
    print("  POST /ledger/redo  {entry_id, actor_id}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
