#!/usr/bin/env python3
"""Local-first, fail-closed MCP server for Sovereignty AI Studio."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from backend.mcp.mcp_governance import (
    CapabilityRecord,
    IdentityContext,
    MCPAuthorityAdapter,
    OperationRequest,
)

PROTOCOL_VERSION = "2025-03-26"
MAX_FILE_BYTES = 1_000_000
MAX_LIST_RESULTS = 200
VALID_MODES = frozenset({"offline", "hybrid", "online", "ghost"})
REPOSITORY_ROOT = Path(__file__).resolve().parent
POLICY_PATH = REPOSITORY_ROOT / "mcp_policy.json"
SENSITIVE_FILE_NAMES = frozenset({".env", ".sg_token_key", ".sg_token_store"})
SENSITIVE_FILE_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx"})


class WorkspaceAnalysisHelper:
    def analyze(self, file_path: Path, relative_path: str) -> dict[str, Any]:
        source = file_path.read_text("utf-8")
        diagnostics = self._syntax_diagnostics(source, file_path.suffix, relative_path)
        diagnostics.extend(self._cleanup_diagnostics(source, file_path.suffix, relative_path))
        return {
            "path": relative_path,
            "language": self._language_name(file_path.suffix),
            "diagnostics": diagnostics,
            "writeAccess": "disabled; review and apply fixes explicitly in the agent branch",
        }

    @staticmethod
    def _language_name(suffix: str) -> str:
        return {".py": "python", ".json": "json"}.get(suffix.lower(), "text")

    def _syntax_diagnostics(self, source: str, suffix: str, relative_path: str) -> list[dict[str, Any]]:
        try:
            if suffix.lower() == ".py":
                compile(source, relative_path, "exec")
            elif suffix.lower() == ".json":
                json.loads(source)
            else:
                return []
        except (SyntaxError, json.JSONDecodeError) as error:
            return [{
                "file": relative_path,
                "line": error.lineno or 1,
                "column": error.offset or 1,
                "severity": "error",
                "rule": "syntax-error",
                "message": error.msg,
                "suggestedAction": "Correct the reported syntax before applying any other cleanup.",
            }]
        return []

    @staticmethod
    def _cleanup_diagnostics(source: str, suffix: str, relative_path: str) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                diagnostics.append({
                    "file": relative_path,
                    "line": line_number,
                    "column": len(line.rstrip(" \t")) + 1,
                    "severity": "warning",
                    "rule": "trailing-whitespace",
                    "message": "Line contains trailing whitespace.",
                    "suggestedAction": "Remove trailing spaces or tabs.",
                })
            if suffix.lower() == ".py" and line.startswith("\t"):
                diagnostics.append({
                    "file": relative_path,
                    "line": line_number,
                    "column": 1,
                    "severity": "warning",
                    "rule": "tab-indentation",
                    "message": "Python indentation starts with a tab.",
                    "suggestedAction": "Use spaces consistently for Python indentation.",
                })
        return diagnostics


class SovereignMCPServer:
    """Bounded read-only MCP provider with an explicit trusted-session boundary."""

    def __init__(
        self,
        workspace: Path | None = None,
        mode: str | None = None,
        identity_context: IdentityContext | None = None,
        policy: dict[str, Any] | None = None,
    ) -> None:
        requested_workspace = workspace or Path(os.environ.get("SG_MCP_WORKSPACE", REPOSITORY_ROOT))
        self.workspace = requested_workspace.resolve()
        requested_mode = mode or os.environ.get("SG_MCP_MODE", "offline")
        self.mode = requested_mode if requested_mode in VALID_MODES else "offline"
        # Environment variables are configuration only. They are never accepted
        # as proof of identity or authority.
        self.identity_context = identity_context
        self.policy = policy if policy is not None else self._load_policy()
        self.authority = MCPAuthorityAdapter(self.policy)

    @staticmethod
    def _load_policy() -> dict[str, Any]:
        try:
            return json.loads(POLICY_PATH.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": "missing", "capabilities": {}}

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if not isinstance(method, str) or request.get("jsonrpc") != "2.0":
            return self._error(request_id, -32600, "Invalid Request")
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return self._result(request_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "sovereignty-ai-studio", "version": "1.2.0"},
            })
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
            {"name": "sovereignty_status", "description": "Report local MCP security boundaries.",
             "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
            {"name": "workspace_list", "description": "List non-hidden files below the configured local workspace.",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "additionalProperties": False}},
            {"name": "workspace_read", "description": "Read a UTF-8 text file below the configured local workspace.",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"name": "workspace_analyze", "description": "Read-only local syntax and cleanup analysis.",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"name": "workspace_repo_status", "description": "Return read-only Git status metadata.",
             "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
        ]

    def _call_tool(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return self._error(request_id, -32602, "Tool name must be a string and arguments an object")

        identity = self.identity_context or IdentityContext(
            identity_id="",
            authenticated=False,
            attestation={},
        )
        operation = name
        op_request = OperationRequest(
            request_id=str(request_id) if request_id is not None else "",
            identity=identity,
            capability=CapabilityRecord(capability_id=name, active=True),
            operation=operation,
            mode=self.mode,
            workspace=str(self.workspace),
        )
        decision = self.authority.authorize(op_request)
        if decision.decision != "ALLOW":
            return self._authorization_result(request_id, decision)

        try:
            if name == "sovereignty_status":
                self._validate_arguments(arguments, set())
                payload = {
                    "mode": self.mode,
                    "workspace": str(self.workspace),
                    "network": "disabled by this MCP server",
                    "credentials": "not accepted, stored, or transmitted",
                    "writes": "disabled; this server only proposes diagnostics",
                }
            elif name == "workspace_list":
                self._validate_arguments(arguments, {"path"})
                payload = self._list_workspace(arguments.get("path", ""))
            elif name == "workspace_read":
                self._validate_arguments(arguments, {"path"}, {"path"})
                payload = self._read_workspace(arguments.get("path"))
            elif name == "workspace_analyze":
                self._validate_arguments(arguments, {"path"}, {"path"})
                payload = self._analyze_workspace(arguments["path"])
            elif name == "workspace_repo_status":
                self._validate_arguments(arguments, set())
                payload = self._repo_status()
            else:
                return self._error(request_id, -32602, f"Unknown tool: {name}")
        except (OSError, ValueError) as error:
            try:
                self.authority.audit.record_execution(request=op_request, result="EXECUTION_ERROR")
            except Exception:
                return self._authorization_failure(request_id, "audit failure after execution error")
            return self._result(request_id, {"content": [{"type": "text", "text": str(error)}], "isError": True})

        try:
            self.authority.audit.record_execution(request=op_request, result="SUCCESS")
        except Exception:
            return self._authorization_failure(request_id, "audit failure after execution")
        return self._result(request_id, {"content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}]})

    @staticmethod
    def _authorization_result(request_id: Any, decision: Any) -> dict[str, Any]:
        return SovereignMCPServer._result(request_id, {
            "content": [{"type": "text", "text": json.dumps({
                "error": "authorization_denied",
                "decision": decision.decision,
                "request_id": decision.request_id,
                "reason": decision.reason,
                "policy_version": decision.policy_version,
            }, sort_keys=True)}],
            "isError": True,
        })

    @staticmethod
    def _authorization_failure(request_id: Any, reason: str) -> dict[str, Any]:
        return SovereignMCPServer._result(request_id, {
            "content": [{"type": "text", "text": json.dumps({
                "error": "authorization_boundary_failure", "reason": reason,
            }, sort_keys=True)}],
            "isError": True,
        })

    @staticmethod
    def _validate_arguments(arguments: dict[str, Any], allowed: set[str], required: set[str] | None = None) -> None:
        unexpected = set(arguments).difference(allowed)
        if unexpected:
            raise ValueError(f"Unsupported tool arguments: {', '.join(sorted(unexpected))}")
        missing = (required or set()).difference(arguments)
        if missing:
            raise ValueError(f"Missing required tool arguments: {', '.join(sorted(missing))}")

    def _resolve_workspace_path(self, relative_path: Any) -> Path:
        if not isinstance(relative_path, str) or not relative_path:
            raise ValueError("A non-empty relative path is required")
        candidate = (self.workspace / relative_path).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as error:
            raise ValueError("Path must remain within the configured workspace") from error
        relative_candidate = candidate.relative_to(self.workspace)
        if self._is_restricted_path(relative_candidate):
            raise ValueError("Hidden and sensitive files are not available through this MCP server")
        return candidate

    @staticmethod
    def _is_restricted_path(relative_path: Path) -> bool:
        return any(part.startswith(".") for part in relative_path.parts) or relative_path.name.lower() in SENSITIVE_FILE_NAMES or relative_path.suffix.lower() in SENSITIVE_FILE_SUFFIXES

    def _list_workspace(self, relative_path: Any) -> dict[str, Any]:
        directory = self.workspace if relative_path == "" else self._resolve_workspace_path(relative_path)
        if not directory.is_dir():
            raise ValueError("Path is not a directory")
        files: list[str] = []
        for item in directory.rglob("*"):
            if len(files) >= MAX_LIST_RESULTS:
                break
            relative_item = item.relative_to(self.workspace)
            if item.is_file() and not self._is_restricted_path(relative_item):
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

    def _analyze_workspace(self, relative_path: Any) -> dict[str, Any]:
        file_path = self._resolve_workspace_path(relative_path)
        if not file_path.is_file():
            raise ValueError("Path is not a file")
        if file_path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"File exceeds {MAX_FILE_BYTES} byte analysis limit")
        return WorkspaceAnalysisHelper().analyze(file_path, str(file_path.relative_to(self.workspace)))

    def _repo_status(self) -> dict[str, Any]:
        def _run(*args: str) -> str:
            try:
                result = subprocess.run(["git", "-C", str(self.workspace), *args], capture_output=True, text=True, timeout=5, check=False)
                return result.stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                return ""
        branch = _run("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
        commit_full = _run("log", "--format=%H", "-1")
        porcelain = _run("status", "--porcelain")
        staged = [line for line in porcelain.splitlines() if len(line) >= 2 and line[0] not in (" ", "?", "!")]
        unstaged = [line for line in porcelain.splitlines() if len(line) >= 2 and line[1] not in (" ", "?", "!")]
        untracked = [line for line in porcelain.splitlines() if line.startswith("??")]
        return {
            "branch": branch,
            "commit": commit_full[:16] if commit_full else "unknown",
            "staged_count": len(staged),
            "unstaged_count": len(unstaged),
            "untracked_count": len(untracked),
            "clean": not (staged or unstaged or untracked),
            "workspace": str(self.workspace),
            "shell_access": "disabled; git is invoked with fixed read-only arguments only",
        }

    @staticmethod
    def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def main() -> None:
    # A raw stdio MCP process has no trusted identity context. It therefore
    # exposes protocol discovery but denies all privileged tools by default.
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
