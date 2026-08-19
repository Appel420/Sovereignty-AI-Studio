#!/usr/bin/env python3
"""Local-only HTTP surface for the Sovereign CI/CD orchestrator."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlparse

from sovereign_cicd_orchestrator import SovereignCICDMOrchestrator

ORCH = SovereignCICDMOrchestrator()
HOST = "127.0.0.1"
PORT = 9898


class CICDServer(BaseHTTPRequestHandler):
    server_version = "SovereignCICD/1.0"

    def _send_json(self, data, code=200):
        payload = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/job/create":
                payload = self._body()
                job = ORCH.create_job(payload.get("repo_path", "."), payload.get("reason", ""))
                return self._send_json({"job_id": job.job_id, "status": "created", "merkle_root": ORCH.merkle.root()})

            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "job":
                job_id, action = parts[1], parts[2]
                if action == "add_step":
                    step = ORCH.add_step(job_id, self._body().get("command", ""))
                    return self._send_json({"step_id": step.step_id, "status": step.status})
                if action == "run_step":
                    step_index = int(self._body().get("step_index", 0))
                    step = ORCH.run_step(job_id, step_index)
                    return self._send_json({"step_id": step.step_id, "status": step.status, "output": step.output[:2000]})
                if action == "finalize":
                    job = ORCH.finalize_job(job_id)
                    return self._send_json({"job_id": job.job_id, "status": job.overall_status, "final_merkle_root": job.final_merkle_root, "pqc_signature": job.pqc_signature})
            self._send_json({"error": "Unknown endpoint"}, 404)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, 400)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 500)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/health":
                return self._send_json({"status": "sovereign_cicd_alive", "active_jobs": len(ORCH.active_jobs)})
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "job" and parts[2] == "status":
                return self._send_json(ORCH.get_status(parts[1]))
            self._send_json({"error": "Unknown endpoint"}, 404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 500)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    print(f"Sovereign CI/CD Server starting on http://{HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), CICDServer)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
