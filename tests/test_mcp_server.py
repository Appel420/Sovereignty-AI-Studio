"""Unit tests for the local-first stdio MCP server."""

import json
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

    def test_notifications_do_not_receive_a_response(self) -> None:
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))


if __name__ == "__main__":
    unittest.main()
