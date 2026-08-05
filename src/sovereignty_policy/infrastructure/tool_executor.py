"""Guarded local tool execution for offline operation.

This module intentionally does not expose arbitrary shells, interpreters,
privilege escalation, recursive deletion, or network clients. Tool calls are
validated before execution and are restricted to an owner-approved workspace.
"""
from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

SAFE_TOOLS = frozenset({"cat", "echo", "grep", "ls"})
SAFE_GREP_FLAGS = frozenset({"-n", "-i", "-l", "-F"})
MAX_OUTPUT_BYTES = 64 * 1024
TIMEOUT_SECONDS = 30


def _response(**values: object) -> str:
    return json.dumps(values, indent=2, sort_keys=True)


def _inside_workspace(workspace: Path, value: str) -> str:
    candidate = (workspace / value).resolve()
    root = workspace.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path escapes the approved workspace")
    return str(candidate)


def _validate_args(tool_name: str, args: Sequence[str]) -> str | None:
    for argument in args:
        if not argument or "\x00" in argument:
            return "empty or NUL-containing arguments are not allowed"
        if any(token in argument for token in (";", "&&", "||", "|", ">", "<", "`", "$(`)):
            return "shell metacharacters are not allowed"
        if argument.startswith("-"):
            if tool_name == "grep" and argument in SAFE_GREP_FLAGS:
                continue
            return f"flag is not permitted: {argument}"
    return None


def execute_tool_call(
    tool_name: str,
    command_args: Sequence[str],
    *,
    workspace: Path,
) -> str:
    """Execute one approved, workspace-scoped, air-gapped inspection call."""
    if tool_name not in SAFE_TOOLS:
        return _response(status="error", error=f"tool is not allowed: {tool_name}")

    root = workspace.resolve()
    if not root.is_dir():
        return _response(status="error", error="approved workspace is not a directory")

    error = _validate_args(tool_name, command_args)
    if error:
        return _response(status="error", error=error)

    try:
        args = list(command_args)
        if tool_name in {"cat", "ls"}:
            args = [(_inside_workspace(root, arg) if not arg.startswith("-") else arg) for arg in args]
        elif tool_name == "grep":
            # grep's pattern is not a path; only the final file operands are scoped.
            non_flags = [index for index, arg in enumerate(args) if not arg.startswith("-")]
            for index in non_flags[1:]:
                args[index] = _inside_workspace(root, args[index])

        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(root),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        result = subprocess.run(
            [tool_name, *args],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=TIMEOUT_SECONDS,
        )
        return _response(
            status="success" if result.returncode == 0 else "error",
            returncode=result.returncode,
            stdout=result.stdout[:MAX_OUTPUT_BYTES],
            stderr=result.stderr[:MAX_OUTPUT_BYTES],
            workspace=str(root),
            network_accessed=False,
        )
    except subprocess.TimeoutExpired:
        return _response(status="error", error="tool execution timed out")
    except OSError as exc:
        return _response(status="error", error=str(exc))
