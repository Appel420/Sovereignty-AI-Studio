#!/usr/bin/env python3
"""
Sovereign CI/CD HTTP Server
Binds to 127.0.0.1:9898 (next to your 9897 Python bridge)
Exposes endpoints for the big Sovereign Validator Dashboard to trigger and monitor jobs.

No external exposure. Local only. Sovereign.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse, parse_qs
from sovereign_cicd_orchestrator import SovereignCICDMOrchestrator

ORCH = SovereignCICDMOrchestrator()
PORT = 9898

class CICDServer(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/job/create":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body)
                repo = payload.get("repo_path", ".")
                reason = payload.get("reason", "")
                job = ORCH.create_job(repo, reason)
                self._send_json({"job_id": job.job_id, "status": "created", "merkle_root": ORCH.merkle.root()})
            except Exception as e:
                self._send_json({"error": str(e)}, 400)

        elif parsed.path.startswith("/job/") and parsed.path.endswith("/add_step"):
            job_id = parsed.path.split("/")[2]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body)
                command = payload.get("command", "")
                step = ORCH.add_step(job_id, command)
                self._send_json({"step_id": step.step_id, "status": step.status})
            except Exception as e:
                self._send_json({"error": str(e)}, 400)

        elif parsed.path.startswith("/job/") and parsed.path.endswith("/run_step"):
            parts = parsed.path.split("/")
            job_id = parts[2]
            step_index = int(parts[4]) if len(parts) > 4 else 0
            try:
                step = ORCH.run_step(job_id, step_index)
                self._send_json({"step_id": step.step_id, "status": step.status, "output": step.output[:2000]})
            except Exception as e:
                self._send_json({"error": str(e)}, 400)

        elif parsed.path.startswith("/job/") and parsed.path.endswith("/finalize"):
            job_id = parsed.path.split("/")[2]
            try:
                job = ORCH.finalize_job(job_id)
                self._send_json({
                    "job_id": job.job_id,
                    "status": job.overall_status,
                    "final_merkle_root": job.final_merkle_root,
                    "pqc_signature": job.pqc_signature
                })
            except Exception as e:
                self._send_json({"error": str(e)}, 400)

        else:
            self._send_json({"error": "Unknown endpoint"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/job/") and parsed.path.endswith("/status"):
            job_id = parsed.path.split("/")[2]
            status = ORCH.get_status(job_id)
            self._send_json(status)
        elif parsed.path == "/health":
            self._send_json({"status": "sovereign_cicd_alive", "active_jobs": len(ORCH.active_jobs)})
        else:
            self._send_json({"error": "Unknown endpoint"}, 404)

if __name__ == "__main__":
    print(f"Sovereign CI/CD Server starting on http://127.0.0.1:{PORT}")
    print("This is YOUR CI/CD. No Google. No GitHub Actions. Root Chain Oversight enforced.")
    server = HTTPServer(("127.0.0.1", PORT), CICDServer)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSovereign CI/CD shutting down.")
