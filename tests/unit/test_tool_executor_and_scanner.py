from pathlib import Path

from sovereignty_policy.infrastructure.sabotage_scanner import scan_path
from sovereignty_policy.infrastructure.tool_executor import execute_tool_call


def test_tool_executor_rejects_interpreters_and_shell_syntax(tmp_path):
    assert '"status": "error"' in execute_tool_call("python", ["-c", "print(1)"], workspace=tmp_path)
    assert '"status": "error"' in execute_tool_call("echo", ["ok; touch x"], workspace=tmp_path)


def test_tool_executor_scopes_paths(tmp_path):
    result = execute_tool_call("cat", ["../secret"], workspace=tmp_path)
    assert "escapes the approved workspace" in result


def test_scanner_is_report_only(tmp_path):
    source = tmp_path / "bad.py"
    source.write_text("def f():\n    try:\n        pass\n    except:\n        pass\n", encoding="utf-8")
    reports = scan_path(tmp_path)
    assert reports[0].findings[0].rule == "bare_except"
    assert source.read_text(encoding="utf-8").startswith("def f")


def test_scanner_detects_subprocess_attribute_calls(tmp_path):
    source = tmp_path / "runner.py"
    source.write_text("import subprocess\nsubprocess.run(['echo', 'ok'])\n", encoding="utf-8")

    reports = scan_path(tmp_path)

    assert reports[0].findings[0].rule == "subprocess_reference"
