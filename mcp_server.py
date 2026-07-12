#!/usr/bin/env python3
"""Local-first Model Context Protocol server for Sovereignty AI Studio.

The server speaks JSON-RPC 2.0 over stdio. It intentionally exposes no
credential, shell, or unrestricted network tools. Hybrid and online modes are
configuration states only; operators must explicitly enable integrations in
their own bridge deployment.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2025-03-26"
MAX_FILE_BYTES = 1_000_000
MAX_LIST_RESULTS = 200
VALID_MODES = frozenset({"offline", "hybrid", "online"})
REPOSITORY_ROOT = Path(__file__).resolve().parent


class SovereignMCPServer:
    """A bounded, credential-free MCP tool provider."""

    def __init__(self, workspace: Path | None = None, mode: str | None = None) -> None:
        requested_workspace = workspace or Path(
            os.environ.get("SG_MCP_WORKSPACE", REPOSITORY_ROOT)
        )
        self.workspace = requested_workspace.resolve()
        requested_mode = mode or os.environ.get("SG_MCP_MODE", "offline")
        self.mode = requested_mode if requested_mode in VALID_MODES else "offline"

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC request, returning None for notifications."""
        method = request.get("method")
        request_id = request.get("id")

        if not isinstance(method, str):
            return self._error(request_id, -32600, "Invalid Request")
        if request.get("jsonrpc") != "2.0":
            return self._error(request_id, -32600, "JSON-RPC version must be 2.0")

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return self._result(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "sovereignty-ai-studio", "version": "1.0.0"},
                },
            )
        if method == "tools/list":
            return self._result(request_id, {"tools": self._tools()})
        if method == "tools/call":
            params = request.get("params", {})
            if not isinstance(params, dict):
                return self._error(request_id, -32602, "Invalid tool parameters")
            return self._call_tool(request_id, params)
        return self._error(request_id, -32601, f"Method not found: {method}")

    def _tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "sovereignty_status",
                "description": "Report the local MCP server mode and its security boundaries.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "workspace_list",
                "description": "List non-hidden files below the configured local workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Optional relative directory within the workspace.",
                        }
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "workspace_read",
                "description": "Read a UTF-8 text file below the configured local workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Required relative file path within the workspace.",
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        ]

    def _call_tool(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return self._error(request_id, -32602, "Tool name and arguments must be objects")

        try:
            if name == "sovereignty_status":
                payload = {
                    "mode": self.mode,
                    "workspace": str(self.workspace),
                    "network": "disabled by this MCP server",
                    "credentials": "not accepted, stored, or transmitted",
                }
            elif name == "workspace_list":
                payload = self._list_workspace(arguments.get("path", ""))
            elif name == "workspace_read":
                payload = self._read_workspace(arguments.get("path"))
            else:
                return self._error(request_id, -32602, f"Unknown tool: {name}")
        except (OSError, ValueError) as error:
            return self._result(
                request_id,
                {"content": [{"type": "text", "text": str(error)}], "isError": True},
            )

        return self._result(
            request_id,
            {"content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}]},
        )

    def _resolve_workspace_path(self, relative_path: Any) -> Path:
        if not isinstance(relative_path, str) or not relative_path:
            raise ValueError("A non-empty relative path is required")
        candidate = (self.workspace / relative_path).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as error:
            raise ValueError("Path must remain within the configured workspace") from error
        return candidate

    def _list_workspace(self, relative_path: Any) -> dict[str, Any]:
        directory = self.workspace if relative_path == "" else self._resolve_workspace_path(relative_path)
        if not directory.is_dir():
            raise ValueError("Path is not a directory")

        files: list[str] = []
        for item in directory.rglob("*"):
            if len(files) >= MAX_LIST_RESULTS:
                break
            if item.is_file() and not any(part.startswith(".") for part in item.relative_to(directory).parts):
                resolved = item.resolve()
                if resolved.is_relative_to(self.workspace):
                    files.append(str(resolved.relative_to(self.workspace)))
        return {"files": sorted(files), "truncated": len(files) == MAX_LIST_RESULTS}

    def _read_workspace(self, relative_path: Any) -> dict[str, str]:
        file_path = self._resolve_workspace_path(relative_path)
        if not file_path.is_file():
            raise ValueError("Path is not a file")
        if file_path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"File exceeds {MAX_FILE_BYTES} byte read limit")
        return {"path": str(file_path.relative_to(self.workspace)), "content": file_path.read_text("utf-8")}

    @staticmethod
    def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def main() -> None:
    """Run the newline-delimited stdio MCP transport."""
    server = SovereignMCPServer()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("Request must be a JSON object")
            response = server.handle(request)
        except (json.JSONDecodeError, ValueError) as error:
            response = SovereignMCPServer._error(None, -32700, str(error))
        if response is not None:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
