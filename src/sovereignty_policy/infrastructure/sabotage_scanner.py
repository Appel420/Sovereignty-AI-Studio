"""Static AI-sabotage pattern scanner.

The scanner is report-only by default. It never edits files, runs discovered
code, contacts remote hosts, or performs automatic fixes.
"""
from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    description: str
    line: int


@dataclass(frozen=True)
class FileReport:
    path: str
    findings: tuple[Finding, ...]


def _python_findings(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return [Finding("syntax_error", "high", str(exc), exc.lineno or 1)]

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(Finding("bare_except", "high", "Bare except masks failures", node.lineno))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            findings.append(Finding("dynamic_execution", "critical", f"Use of {node.func.id} detected", node.lineno))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "subprocess":
            findings.append(Finding("subprocess_reference", "medium", "Review subprocess use", node.lineno))
    return findings


def scan_path(root: Path) -> list[FileReport]:
    reports: list[FileReport] = []
    excluded = {".git", "node_modules", ".venv", "venv", ".asav_quarantine"}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        findings = _python_findings(path, text) if path.suffix == ".py" else []
        if findings:
            reports.append(FileReport(str(path.relative_to(root)), tuple(findings)))
    return reports


def report_json(reports: list[FileReport]) -> str:
    return json.dumps({"results": [asdict(report) for report in reports]}, indent=2, sort_keys=True)
