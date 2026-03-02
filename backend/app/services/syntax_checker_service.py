"""
Syntax Checker Service with Color-Coded Error Output
Validates Python code and provides structured error reports
with severity-based color coding for dashboard display.
"""
import ast
import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# Color codes for frontend rendering
SEVERITY_COLORS = {
    ErrorSeverity.ERROR: "#EF4444",     # Red
    ErrorSeverity.WARNING: "#F59E0B",   # Amber
    ErrorSeverity.INFO: "#3B82F6",      # Blue
}


class SyntaxCheckerService:
    """
    Service for checking Python code syntax with color-coded error reporting.
    Designed for dashboard integration with structured error output.
    """

    def check_syntax(self, code: str, filename: str = "<input>") -> Dict[str, Any]:
        """
        Check Python code for syntax errors.

        Args:
            code: Python source code string
            filename: Optional filename for error messages

        Returns:
            Dictionary with check results, errors, and color coding
        """
        errors: List[Dict[str, Any]] = []

        # Check for syntax errors using ast.parse
        try:
            ast.parse(code, filename=filename)
        except SyntaxError as e:
            errors.append({
                "type": "SyntaxError",
                "message": str(e.msg) if e.msg else "Invalid syntax",
                "line": e.lineno,
                "column": e.offset,
                "severity": ErrorSeverity.ERROR.value,
                "color": SEVERITY_COLORS[ErrorSeverity.ERROR],
                "text": e.text.rstrip() if e.text else "",
            })

        # Check for common issues via compile
        if not errors:
            try:
                compile(code, filename, "exec")
            except SyntaxError as e:
                errors.append({
                    "type": "CompileError",
                    "message": str(e.msg) if e.msg else "Compilation error",
                    "line": e.lineno,
                    "column": e.offset,
                    "severity": ErrorSeverity.ERROR.value,
                    "color": SEVERITY_COLORS[ErrorSeverity.ERROR],
                    "text": e.text.rstrip() if e.text else "",
                })

        # Lint-level warnings (basic checks)
        warnings = self._check_warnings(code)
        errors.extend(warnings)

        return {
            "valid": len([e for e in errors if e["severity"] == "error"]) == 0,
            "errors": errors,
            "error_count": len([e for e in errors if e["severity"] == "error"]),
            "warning_count": len([e for e in errors if e["severity"] == "warning"]),
            "info_count": len([e for e in errors if e["severity"] == "info"]),
            "color_legend": {
                "error": SEVERITY_COLORS[ErrorSeverity.ERROR],
                "warning": SEVERITY_COLORS[ErrorSeverity.WARNING],
                "info": SEVERITY_COLORS[ErrorSeverity.INFO],
            },
        }

    def _check_warnings(self, code: str) -> List[Dict[str, Any]]:
        """Check for common code warnings."""
        warnings = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check for bare except
            if stripped == "except:":
                warnings.append({
                    "type": "BareExcept",
                    "message": "Bare except clause - consider catching specific exceptions",
                    "line": i,
                    "column": 1,
                    "severity": ErrorSeverity.WARNING.value,
                    "color": SEVERITY_COLORS[ErrorSeverity.WARNING],
                    "text": line.rstrip(),
                })

            # Check for eval usage
            if "eval(" in stripped:
                warnings.append({
                    "type": "SecurityWarning",
                    "message": "Use of eval() is a security risk",
                    "line": i,
                    "column": line.index("eval(") + 1,
                    "severity": ErrorSeverity.WARNING.value,
                    "color": SEVERITY_COLORS[ErrorSeverity.WARNING],
                    "text": line.rstrip(),
                })

            # Check for exec usage
            if "exec(" in stripped:
                warnings.append({
                    "type": "SecurityWarning",
                    "message": "Use of exec() is a security risk",
                    "line": i,
                    "column": line.index("exec(") + 1,
                    "severity": ErrorSeverity.WARNING.value,
                    "color": SEVERITY_COLORS[ErrorSeverity.WARNING],
                    "text": line.rstrip(),
                })

        return warnings


# Global instance
syntax_checker = SyntaxCheckerService()
