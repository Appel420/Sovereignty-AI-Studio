"""Test the local branch ownership validation contract."""
from __future__ import annotations

import subprocess
import sys


def test_unknown_branch_fails_closed() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate-branch-ownership.py", "--branch", "main"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "valid" in result.stdout
