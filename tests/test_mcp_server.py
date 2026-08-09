"""Unit and governance tests for the fail-closed local MCP boundary."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.mcp.mcp_governance import IdentityContext
from mcp_server import PROTOCOL_VERSION, SovereignMCPServer


ATTESTED_IDENTITY = "owner-local"
ATTESTATION = {
    "trust_boundary": "local-only",
    "network": False,
    "credentials": False,
    "mutation": False,
    "shell": False,
}


def authorized_identity() -> IdentityContext:
    return IdentityContext(
        identity_id=ATTESTED_IDENTITY,
        authenticated=True,
        attestation=ATTESTATION,
    )


class SovereignMCPServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "notes.txt").write_text("local data", encoding="utf-8")
        (self.workspace / ".secret").write_text("hidden", encoding="utf-8")
        (self.workspace / ".env").write_text("TOKEN=private", encoding="utf-8")
        (self.workspace / "private.pem").write_text("private", encoding="utf-8")
        self.server = SovereignMCPServer(
            workspace=self.workspace,
            identity_context=authorized_identity(),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def request(self, method: str, params: dict | None = None) -> dict:
        request = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params is not None:
            request["params"] = params
        return self.server.handle(request)  # type: ignore[return-value]

    def tool_text(self, name: str, arguments: dict | None = None) -> dict:
        response = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        return json.loads(response["result"]["content"][0]["text"])

    def test_initialize_advertises_standard_protocol_and_tools(self) -> None:
        response = self.request("initialize")
        self.assertEqual(response["result"]["protocolVersion"], PROTOCOL_VERSION)
        self.assertIn("tools", response["result"]["capabilities"])

    def test_anonymous_workspace_call_is_denied_and_audited(self) -> None:
        server = SovereignMCPServer(workspace=self.workspace)
        response = server.handle({
            "jsonrpc": "2.0",
            "id": "anon-1",
            "method": "tools/call",
            "params": {"name": "workspace_list", "arguments": {}},
        })
        self.assertTrue(response["result"]["isError"])
        denial = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(denial["decision"], "DENY")
        event = server.authority.audit.events[-1]
        self.assertEqual(event["request_id"], "anon-1")
        self.assertEqual(event["identity_id"], "")
        self.assertEqual(event["decision"], "DENY")
        self.assertNotIn("local data", json.dumps(event))

    def test_identity_name_without_authenticated_session_is_denied(self) -> None:
        server = SovereignMCPServer(
            workspace=self.workspace,
            identity_context=IdentityContext(
                identity_id=ATTESTED_IDENTITY,
                authenticated=False,
                attestation=ATTESTATION,
            ),
        )
        response = server.handle({
            "jsonrpc": "2.0",
            "id": "unauth-1",
            "method": "tools/call",
            "params": {"name": "workspace_list", "arguments": {}},
        })
        denial = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(denial["reason"], "unauthenticated identity")

    def test_invalid_attestation_is_denied(self) -> None:
        server = SovereignMCPServer(
            workspace=self.workspace,
            identity_context=IdentityContext(
                identity_id=ATTESTED_IDENTITY,
                authenticated=True,
                attestation={"network": True},
            ),
        )
        response = server.handle({
            "jsonrpc": "2.0",
            "id": "bad-attestation",
            "method": "tools/call",
            "params": {"name": "workspace_list", "arguments": {}},
        })
        denial = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(denial["reason"], "invalid local attestation")

    def test_authorized_workspace_list_executes_and_is_audited(self) -> None:
        listing = self.tool_text("workspace_list")
        self.assertEqual(listing["files"], ["notes.txt"])
        events = self.server.authority.audit.events
        self.assertEqual(events[-2]["decision"], "ALLOW")
        self.assertEqual(events[-2]["identity_id"], ATTESTED_IDENTITY)
        self.assertEqual(events[-2]["capability_id"], "workspace_list")
        self.assertEqual(events[-1]["event"], "MCP_EXECUTION_RESULT")
        self.assertEqual(events[-1]["result"], "SUCCESS")

    def test_authorized_workspace_read_preserves_containment(self) -> None:
        content = self.tool_text("workspace_read", {"path": "notes.txt"})
        self.assertEqual(content["content"], "local data")
        response = self.request("tools/call", {"name": "workspace_read", "arguments": {"path": "../etc/passwd"}})
        self.assertTrue(response["result"]["isError"])

    def test_workspace_tools_exclude_hidden_and_sensitive_files(self) -> None:
        for path in (".secret", ".env", "private.pem"):
            response = self.request("tools/call", {"name": "workspace_read", "arguments": {"path": path}})
            self.assertTrue(response["result"]["isError"])
            self.assertIn("Hidden and sensitive files", response["result"]["content"][0]["text"])

    def test_analysis_returns_structured_syntax_and_cleanup_diagnostics(self) -> None:
        (self.workspace / "broken.py").write_text("def bad(:  \n", encoding="utf-8")
        result = self.tool_text("workspace_analyze", {"path": "broken.py"})
        self.assertEqual(result["path"], "broken.py")
        self.assertEqual(result["writeAccess"], "disabled; review and apply fixes explicitly in the agent branch")
        self.assertEqual(result["diagnostics"][0]["rule"], "syntax-error")
        self.assertTrue(any(item["rule"] == "trailing-whitespace" for item in result["diagnostics"]))

    def test_analysis_reports_unsupported_arguments(self) -> None:
        malformed = self.request("tools/call", {"name": "workspace_analyze", "arguments": {"path": "notes.txt", "extra": True}})
        self.assertTrue(malformed["result"]["isError"])
        self.assertIn("Unsupported tool arguments", malformed["result"]["content"][0]["text"])

    def test_notifications_do_not_receive_a_response(self) -> None:
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_repo_status_tool_is_listed(self) -> None:
        response = self.request("tools/list")
        tool_names = [tool["name"] for tool in response["result"]["tools"]]
        self.assertIn("workspace_repo_status", tool_names)

    def test_repo_status_rejects_unexpected_arguments(self) -> None:
        response = self.request("tools/call", {"name": "workspace_repo_status", "arguments": {"extra": "bad"}})
        self.assertTrue(response["result"]["isError"])
        self.assertIn("Unsupported tool arguments", response["result"]["content"][0]["text"])

    def test_repo_status_returns_safe_fields_in_non_git_directory(self) -> None:
        result = self.tool_text("workspace_repo_status")
        for key in ("branch", "commit", "staged_count", "unstaged_count", "untracked_count", "clean", "workspace", "shell_access"):
            self.assertIn(key, result)
        for key in ("staged_count", "unstaged_count", "untracked_count"):
            self.assertIsInstance(result[key], int)
            self.assertGreaterEqual(result[key], 0)
        self.assertIsInstance(result["clean"], bool)
        self.assertIn("disabled", result["shell_access"])

    def test_repo_status_in_real_git_repo(self) -> None:
        server_in_repo = SovereignMCPServer(workspace=Path.cwd(), identity_context=authorized_identity())
        try:
            subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.skipTest("Not inside a git repository or git not available")
        result = server_in_repo.handle({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "workspace_repo_status", "arguments": {}},
        })
        self.assertNotEqual(json.loads(result["result"]["content"][0]["text"])["branch"], "")


if __name__ == "__main__":
    unittest.main()
