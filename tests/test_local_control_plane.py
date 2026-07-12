"""Tests for the loopback-only Local Control Plane dashboard server.

Validates that:
- DashboardServer unconditionally refuses non-loopback bind addresses.
- Each data-builder returns the required JSON structure.
- The in-process audit ring-buffer records and caps entries correctly.
- The HTTP handler routes requests and enforces loopback-only access.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Import bridge/serve_dashboard.py directly by file path to avoid the
# name collision between top-level bridge.py and the bridge/ subdirectory.
# ---------------------------------------------------------------------------

_SERVE_DASHBOARD_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "bridge" / "serve_dashboard.py"
)
_spec = importlib.util.spec_from_file_location("serve_dashboard", _SERVE_DASHBOARD_PATH)
_sd = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_sd)  # type: ignore[union-attr]

DashboardServer = _sd.DashboardServer
_DashboardHandler = _sd._DashboardHandler
_agent_status = _sd._agent_status
_audit_log = _sd._audit_log
_audit_lock = _sd._audit_lock
_cicd_status = _sd._cicd_status
_network_audit = _sd._network_audit
_record_audit = _sd._record_audit
_repo_status = _sd._repo_status


# ---------------------------------------------------------------------------
# Helper — spin up a real loopback HTTP server for integration-style tests
# ---------------------------------------------------------------------------


def _start_test_server():
    """Start a DashboardServer on a random loopback port; return (server, port)."""
    from http.server import HTTPServer
    srv = HTTPServer(("127.0.0.1", 0), _DashboardHandler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, port


def _get_json(port: int, path: str) -> dict:
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read())


# ---------------------------------------------------------------------------
# Unit tests — data builders
# ---------------------------------------------------------------------------


class TestRepoStatus(unittest.TestCase):
    def test_returns_required_fields(self) -> None:
        result = _repo_status()
        for key in ("branch", "commit", "staged_count", "unstaged_count", "untracked_count", "clean", "shell_access"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_counts_are_non_negative_integers(self) -> None:
        result = _repo_status()
        for key in ("staged_count", "unstaged_count", "untracked_count"):
            self.assertIsInstance(result[key], int)
            self.assertGreaterEqual(result[key], 0)

    def test_clean_is_boolean(self) -> None:
        result = _repo_status()
        self.assertIsInstance(result["clean"], bool)

    def test_shell_access_is_disabled(self) -> None:
        result = _repo_status()
        self.assertEqual(result["shell_access"], "disabled")

    def test_branch_is_string(self) -> None:
        result = _repo_status()
        self.assertIsInstance(result["branch"], str)
        self.assertTrue(result["branch"])  # non-empty

    def test_commit_is_string(self) -> None:
        result = _repo_status()
        self.assertIsInstance(result["commit"], str)
        self.assertTrue(result["commit"])  # non-empty


class TestAgentStatus(unittest.TestCase):
    def test_returns_required_fields(self) -> None:
        result = _agent_status()
        for key in ("agent_modules", "count", "source"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_agent_modules_is_list(self) -> None:
        result = _agent_status()
        self.assertIsInstance(result["agent_modules"], list)

    def test_count_matches_modules_length(self) -> None:
        result = _agent_status()
        self.assertEqual(result["count"], len(result["agent_modules"]))

    def test_source_indicates_local_scan(self) -> None:
        result = _agent_status()
        self.assertEqual(result["source"], "local-file-scan")


class TestCICDStatus(unittest.TestCase):
    def test_returns_required_fields(self) -> None:
        result = _cicd_status()
        for key in ("workflows", "count", "source"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_workflows_is_list(self) -> None:
        result = _cicd_status()
        self.assertIsInstance(result["workflows"], list)

    def test_count_matches_workflows_length(self) -> None:
        result = _cicd_status()
        self.assertEqual(result["count"], len(result["workflows"]))

    def test_workflow_entries_have_name_and_file(self) -> None:
        result = _cicd_status()
        for wf in result["workflows"]:
            self.assertIn("name", wf)
            self.assertIn("file", wf)

    def test_source_indicates_local_scan(self) -> None:
        result = _cicd_status()
        self.assertEqual(result["source"], "local-workflow-scan")


class TestNetworkAudit(unittest.TestCase):
    def setUp(self) -> None:
        # Clear the audit log before each test.
        with _audit_lock:
            _audit_log.clear()

    def test_returns_required_fields(self) -> None:
        result = _network_audit()
        self.assertIn("entries", result)
        self.assertIn("total", result)

    def test_recorded_entries_appear_in_output(self) -> None:
        _record_audit("TEST_EVENT", "test detail")
        result = _network_audit()
        self.assertGreater(result["total"], 0)
        last = result["entries"][-1]
        self.assertEqual(last["event"], "TEST_EVENT")
        self.assertEqual(last["detail"], "test detail")

    def test_entries_capped_at_200(self) -> None:
        for i in range(250):
            _record_audit("OVERFLOW", str(i))
        with _audit_lock:
            self.assertLessEqual(len(_audit_log), 200)

    def test_entries_have_timestamp(self) -> None:
        _record_audit("TS_CHECK", "ts")
        result = _network_audit()
        entry = result["entries"][-1]
        self.assertIn("ts", entry)
        self.assertIsInstance(entry["ts"], float)


# ---------------------------------------------------------------------------
# Unit tests — DashboardServer construction
# ---------------------------------------------------------------------------


class TestDashboardServerConstruction(unittest.TestCase):
    def test_loopback_127_accepted(self) -> None:
        srv = DashboardServer(host="127.0.0.1", port=9898)
        self.assertEqual(srv.host, "127.0.0.1")

    def test_localhost_accepted(self) -> None:
        srv = DashboardServer(host="localhost", port=9898)
        self.assertEqual(srv.host, "localhost")

    def test_non_loopback_rejected(self) -> None:
        for bad in ("0.0.0.0", "192.168.1.1", "10.0.0.1", ""):
            with self.assertRaises(ValueError, msg=f"Expected ValueError for host={bad!r}"):
                DashboardServer(host=bad, port=9898)

    def test_record_audit_static_method_works(self) -> None:
        with _audit_lock:
            _audit_log.clear()
        DashboardServer.record_audit("STATIC_TEST", "from test")
        with _audit_lock:
            last = _audit_log[-1]
        self.assertEqual(last["event"], "STATIC_TEST")


# ---------------------------------------------------------------------------
# Integration tests — HTTP endpoints via real loopback server
# ---------------------------------------------------------------------------


class TestDashboardEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server, cls.port = _start_test_server()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def test_health_endpoint_returns_ok(self) -> None:
        data = _get_json(self.port, "/health")
        self.assertEqual(data["status"], "ok")

    def test_api_health_endpoint_returns_ok(self) -> None:
        data = _get_json(self.port, "/api/health")
        self.assertEqual(data["status"], "ok")

    def test_repo_status_endpoint(self) -> None:
        data = _get_json(self.port, "/api/repo-status")
        self.assertIn("branch", data)
        self.assertIn("clean", data)
        self.assertEqual(data["shell_access"], "disabled")

    def test_agent_status_endpoint(self) -> None:
        data = _get_json(self.port, "/api/agent-status")
        self.assertIn("agent_modules", data)
        self.assertIn("count", data)

    def test_cicd_status_endpoint(self) -> None:
        data = _get_json(self.port, "/api/cicd-status")
        self.assertIn("workflows", data)
        self.assertIn("count", data)

    def test_network_audit_endpoint(self) -> None:
        data = _get_json(self.port, "/api/network-audit")
        self.assertIn("entries", data)
        self.assertIn("total", data)

    def test_unknown_path_returns_404(self) -> None:
        try:
            _get_json(self.port, "/api/unknown-endpoint")
            self.fail("Expected HTTP 404")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 404)

    def test_response_has_no_store_cache_control(self) -> None:
        url = f"http://127.0.0.1:{self.port}/health"
        with urllib.request.urlopen(url, timeout=5) as r:
            cc = r.headers.get("Cache-Control", "")
        self.assertIn("no-store", cc)

    def test_response_cors_origin_is_loopback(self) -> None:
        url = f"http://127.0.0.1:{self.port}/health"
        with urllib.request.urlopen(url, timeout=5) as r:
            acao = r.headers.get("Access-Control-Allow-Origin", "")
        # Must be a loopback origin (or empty if no Origin header was sent).
        self.assertTrue(
            acao == "" or "127.0.0.1" in acao or "localhost" in acao,
            f"Unexpected CORS origin: {acao!r}",
        )

    def test_every_request_is_audited(self) -> None:
        with _audit_lock:
            before = len(_audit_log)
        _get_json(self.port, "/health")
        time.sleep(0.05)
        with _audit_lock:
            after = len(_audit_log)
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
