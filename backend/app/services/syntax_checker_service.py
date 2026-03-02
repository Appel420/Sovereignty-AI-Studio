"""
Syntax Checker Service – colour-coded error detection and display.

Analyses source code for syntax errors, provides ANSI colour-coded output,
and classifies issues by severity (error, warning, info).
"""
import ast
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ANSI colour codes for terminal output
COLOUR_MAP = {
    Severity.ERROR: "\033[91m",    # Red
    Severity.WARNING: "\033[93m",  # Yellow
    Severity.INFO: "\033[96m",     # Cyan
}
COLOUR_RESET = "\033[0m"
COLOUR_BOLD = "\033[1m"
COLOUR_LINE = "\033[90m"  # Grey for line numbers


@dataclass
class SyntaxIssue:
    """Represents a detected syntax issue."""
    file_path: str
    line: int
    column: int
    severity: Severity
    message: str
    code_snippet: str = ""


class SyntaxCheckerService:
    """Analyses code for syntax errors with colour-coded output."""

    def __init__(self):
        logger.info("SyntaxCheckerService initialised")

    def check_python(
        self, source: str, file_path: str = "<input>"
    ) -> Dict[str, Any]:
        """Check Python source code for syntax errors.

        Returns a structured report with colour-coded display strings.
        """
        issues: List[SyntaxIssue] = []

        # AST-level syntax check
        try:
            ast.parse(source, filename=file_path)
        except SyntaxError as exc:
            issues.append(SyntaxIssue(
                file_path=file_path,
                line=exc.lineno or 0,
                column=exc.offset or 0,
                severity=Severity.ERROR,
                message=str(exc.msg),
                code_snippet=exc.text or "",
            ))

        # Basic heuristic checks
        issues.extend(self._heuristic_checks(source, file_path))

        return self._build_report(issues, file_path)

    def check_file(self, file_path: str) -> Dict[str, Any]:
        """Check a file on disk for syntax errors."""
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                source = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            return {
                "file": file_path,
                "success": False,
                "error": str(exc),
                "issues": [],
            }
        return self.check_python(source, file_path)

    def format_coloured(self, report: Dict[str, Any]) -> str:
        """Return a colour-coded string for terminal display."""
        lines = []
        for issue in report.get("issues", []):
            sev = Severity(issue["severity"])
            colour = COLOUR_MAP.get(sev, "")
            tag = f"{colour}{COLOUR_BOLD}[{sev.value.upper()}]{COLOUR_RESET}"
            loc = (
                f"{COLOUR_LINE}{issue['file_path']}:{issue['line']}"
                f":{issue['column']}{COLOUR_RESET}"
            )
            lines.append(f"{tag} {loc} {issue['message']}")
            if issue.get("code_snippet"):
                lines.append(f"  {COLOUR_LINE}>{COLOUR_RESET} {issue['code_snippet']}")
        if not lines:
            return f"\033[92m✓ No issues found in {report.get('file', 'input')}{COLOUR_RESET}"
        return "\n".join(lines)

    def get_status(self) -> Dict[str, Any]:
        return {
            "service": "syntax_checker",
            "status": "online",
            "supported_languages": ["python"],
            "colour_coded": True,
        }

    # ── Private helpers ──────────────────────────────────────────────

    def _heuristic_checks(
        self, source: str, file_path: str
    ) -> List[SyntaxIssue]:
        """Run lightweight heuristic checks on source code."""
        issues: List[SyntaxIssue] = []
        lines = source.splitlines()

        for idx, line in enumerate(lines, start=1):
            stripped = line.rstrip()

            # Trailing whitespace
            if line != stripped and stripped:
                issues.append(SyntaxIssue(
                    file_path=file_path,
                    line=idx,
                    column=len(stripped) + 1,
                    severity=Severity.INFO,
                    message="Trailing whitespace",
                ))

            # Mixed tabs and spaces
            leading = line[: len(line) - len(line.lstrip())]
            if "\t" in leading and " " in leading:
                issues.append(SyntaxIssue(
                    file_path=file_path,
                    line=idx,
                    column=1,
                    severity=Severity.WARNING,
                    message="Mixed tabs and spaces in indentation",
                ))

        return issues

    def _build_report(
        self, issues: List[SyntaxIssue], file_path: str
    ) -> Dict[str, Any]:
        """Build a structured report from detected issues."""
        issue_dicts = [
            {
                "file_path": i.file_path,
                "line": i.line,
                "column": i.column,
                "severity": i.severity.value,
                "message": i.message,
                "code_snippet": i.code_snippet,
            }
            for i in issues
        ]
        errors = sum(1 for i in issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
        return {
            "file": file_path,
            "success": errors == 0,
            "total_issues": len(issues),
            "errors": errors,
            "warnings": warnings,
            "info": len(issues) - errors - warnings,
            "issues": issue_dicts,
        }


# Module-level singleton
syntax_checker_service = SyntaxCheckerService()
