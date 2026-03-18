"""
Telemetry service — metrics collection for AI requests, provider usage, latency, errors.
Uses in-memory counters (no Prometheus SDK dependency at runtime —
exposes data compatible with a Prometheus scraper via /api/telemetry/metrics).
"""
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List


class MetricsStore:
    """Thread-safe in-memory metrics store."""

    def __init__(self):
        self._lock = threading.Lock()
        self._request_count: Dict[str, int] = defaultdict(int)
        self._error_count: Dict[str, int] = defaultdict(int)
        self._latency_sum: Dict[str, float] = defaultdict(float)
        self._latency_count: Dict[str, int] = defaultdict(int)
        self._token_count: Dict[str, int] = defaultdict(int)
        self._started_at = datetime.now(tz=timezone.utc).isoformat()

    # ── Record ─────────────────────────────────────────────────────────────────

    def record_ai_request(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        success: bool = True,
    ) -> None:
        key = f"{provider}:{model}"
        with self._lock:
            self._request_count[key] += 1
            self._latency_sum[key] += latency_ms
            self._latency_count[key] += 1
            self._token_count[key] += prompt_tokens + completion_tokens
            if not success:
                self._error_count[key] += 1

    def record_api_call(self, endpoint: str, status_code: int, latency_ms: float) -> None:
        key = f"api:{endpoint}"
        with self._lock:
            self._request_count[key] += 1
            self._latency_sum[key] += latency_ms
            self._latency_count[key] += 1
            if status_code >= 400:
                self._error_count[key] += 1

    # ── Query ──────────────────────────────────────────────────────────────────

    def get_metrics(self) -> dict:
        with self._lock:
            providers = {}
            for key in set(self._request_count) | set(self._error_count):
                if not key.startswith("api:"):
                    provider, model = key.split(":", 1)
                    requests = self._request_count.get(key, 0)
                    errors = self._error_count.get(key, 0)
                    lat_sum = self._latency_sum.get(key, 0.0)
                    lat_cnt = self._latency_count.get(key, 0)
                    avg_lat = round(lat_sum / lat_cnt, 2) if lat_cnt > 0 else 0.0
                    providers.setdefault(provider, {})[model] = {
                        "requests": requests,
                        "errors": errors,
                        "error_rate": round(errors / requests, 4) if requests else 0.0,
                        "avg_latency_ms": avg_lat,
                        "total_tokens": self._token_count.get(key, 0),
                    }

            api_endpoints = {}
            for key in self._request_count:
                if key.startswith("api:"):
                    endpoint = key[4:]
                    requests = self._request_count[key]
                    errors = self._error_count.get(key, 0)
                    lat_sum = self._latency_sum.get(key, 0.0)
                    lat_cnt = self._latency_count.get(key, 0)
                    api_endpoints[endpoint] = {
                        "requests": requests,
                        "errors": errors,
                        "avg_latency_ms": round(lat_sum / lat_cnt, 2) if lat_cnt else 0.0,
                    }

            total_requests = sum(
                v for k, v in self._request_count.items() if not k.startswith("api:")
            )
            total_errors = sum(
                v for k, v in self._error_count.items() if not k.startswith("api:")
            )

        return {
            "started_at": self._started_at,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "ai_requests": {
                "total": total_requests,
                "errors": total_errors,
                "error_rate": round(total_errors / total_requests, 4) if total_requests else 0.0,
            },
            "by_provider": providers,
            "api_endpoints": api_endpoints,
        }

    def prometheus_format(self) -> str:
        """Emit Prometheus text format metrics."""
        lines: List[str] = [
            "# HELP sovereignty_ai_requests_total Total AI requests",
            "# TYPE sovereignty_ai_requests_total counter",
        ]
        with self._lock:
            for key, count in self._request_count.items():
                if not key.startswith("api:"):
                    provider, model = key.split(":", 1)
                    lines.append(
                        f'sovereignty_ai_requests_total{{provider="{provider}",model="{model}"}} {count}'
                    )
            lines.append("# HELP sovereignty_ai_errors_total Total AI errors")
            lines.append("# TYPE sovereignty_ai_errors_total counter")
            for key, count in self._error_count.items():
                if not key.startswith("api:"):
                    provider, model = key.split(":", 1)
                    lines.append(
                        f'sovereignty_ai_errors_total{{provider="{provider}",model="{model}"}} {count}'
                    )
        return "\n".join(lines) + "\n"


# Module-level singleton
telemetry = MetricsStore()
