"""Minimal Prometheus-style metrics helpers."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass
class MetricsHandle:
    server: ThreadingHTTPServer
    thread: threading.Thread

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def init_metrics(namespace: str = "sovereignty", labels: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "namespace": namespace,
        "labels": labels or {},
        "counters": {},
        "gauges": {},
    }


def start_metrics_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    metrics: dict[str, Any] | None = None,
) -> MetricsHandle:
    payload = metrics or init_metrics()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in {"/metrics", "/health"}:
                self.send_response(404)
                self.end_headers()
                return

            body = "\n".join(
                [
                    f'# HELP {payload["namespace"]}_up Service availability',
                    f'# TYPE {payload["namespace"]}_up gauge',
                    f'{payload["namespace"]}_up 1',
                ]
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return None

    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return MetricsHandle(server=server, thread=thread)