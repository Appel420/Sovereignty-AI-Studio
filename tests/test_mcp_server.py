"""Unit tests for the local-first stdio MCP server."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from mcp_server import PROTOCOL_VERSION, SovereignMCPServer


class SovereignMCPServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "notes.txt").write_text("local data", encoding="utf-8")
        (self.workspace / ".secret").write_text("hidden", encoding="utf-8")
        (self.workspace / ".env").write_text("TOKEN=private", encoding="utf-8")
        (self.workspace / "private.pem").write_text("private", encoding="utf-8")
        self.server = SovereignMCPServer(workspace=self.workspace)

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

    def test_status_is_offline_and_credential_free_by_default(self) -> None:
        status = self.tool_text("sovereignty_status")
        self.assertEqual(status["mode"], "offline")
        self.assertEqual(status["network"], "disabled by this MCP server")
        self.assertEqual(status["credentials"], "not accepted, stored, or transmitted")

    def test_workspace_tools_are_bounded_to_configured_workspace(self) -> None:
        listing = self.tool_text("workspace_list")
        self.assertEqual(listing["files"], ["notes.txt"])
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
        self.assertEqual(result["diagnostics"][0]["line"], 1)
        self.assertTrue(any(item["rule"] == "trailing-whitespace" for item in result["diagnostics"]))

    def test_analysis_reports_unsupported_arguments_and_restricted_paths(self) -> None:
        malformed = self.request(
            "tools/call", {"name": "workspace_analyze", "arguments": {"path": "notes.txt", "extra": True}}
        )
        self.assertTrue(malformed["result"]["isError"])
        self.assertIn("Unsupported tool arguments", malformed["result"]["content"][0]["text"])

        restricted = self.request("tools/call", {"name": "workspace_analyze", "arguments": {"path": ".env"}})
        self.assertTrue(restricted["result"]["isError"])
        self.assertIn("Hidden and sensitive files", restricted["result"]["content"][0]["text"])

    def test_notifications_do_not_receive_a_response(self) -> None:
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    # ------------------------------------------------------------------
    # workspace_repo_status tests
    # ------------------------------------------------------------------

    def test_repo_status_tool_is_listed(self) -> None:
        response = self.request("tools/list")
        tool_names = [t["name"] for t in response["result"]["tools"]]
        self.assertIn("workspace_repo_status", tool_names)

    def test_repo_status_rejects_unexpected_arguments(self) -> None:
        response = self.request(
            "tools/call",
            {"name": "workspace_repo_status", "arguments": {"extra": "bad"}},
        )
        self.assertTrue(response["result"]["isError"])
        self.assertIn("Unsupported tool arguments", response["result"]["content"][0]["text"])

    def test_repo_status_returns_expected_fields_in_non_git_directory(self) -> None:
        """In a temp dir with no git repo every field must still be present and safe."""
        result = self.tool_text("workspace_repo_status")
        # All required keys must be present regardless of git availability.
        for key in ("branch", "commit", "staged_count", "unstaged_count", "untracked_count", "clean", "workspace", "shell_access"):
            self.assertIn(key, result, f"Missing key: {key}")
        # Counts must be non-negative integers.
        for key in ("staged_count", "unstaged_count", "untracked_count"):
            self.assertIsInstance(result[key], int)
            self.assertGreaterEqual(result[key], 0)
        # clean must be a bool.
        self.assertIsInstance(result["clean"], bool)
        # shell_access must explicitly state it is disabled.
        self.assertIn("disabled", result["shell_access"])
        # workspace must be a non-empty string.
        self.assertIsInstance(result["workspace"], str)
        self.assertTrue(result["workspace"])

    def test_repo_status_graceful_when_git_absent(self) -> None:
        """If git is not available or the directory is not a repo, return safe defaults."""
        result = self.tool_text("workspace_repo_status")
        # branch and commit must be strings (may be "unknown" when git is not a repo).
        self.assertIsInstance(result["branch"], str)
        self.assertIsInstance(result["commit"], str)

    def test_repo_status_in_real_git_repo(self) -> None:
        """If the current process is running inside a git repo, branch must not be empty."""
        import os
        server_in_repo = SovereignMCPServer(workspace=Path(os.getcwd()))
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True, check=True, timeout=5,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.skipTest("Not inside a git repository or git not available")

        response = server_in_repo.handle(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "workspace_repo_status", "arguments": {}}}
        )
        result = json.loads(response["result"]["content"][0]["text"])
        self.assertNotEqual(result["branch"], "")
        self.assertNotEqual(result["branch"], None)


if __name__ == "__main__":
    unittest.main()
