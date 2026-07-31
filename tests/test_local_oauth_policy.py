"""Offline OAuth contract tests."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]


def test_policy_selects_canonical_local_generator() -> None:
    policy = json.loads((ROOT / "config/local-oauth-policy.json").read_text())
    assert policy["issuer"] == "local"
    assert policy["generator"] == "scripts/oauth_local_generator.py"
    assert policy["network_access"] is False
    assert policy["external_oauth"] == "disabled"


def test_canonical_generator_dry_run_is_network_free() -> None:
    script = ROOT / "scripts/oauth_local_generator.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["issuer"] == "local"
    assert report["network_accessed"] is False
    assert report["generation"] == "SKIPPED"
    assert report["persistence"] == "SKIPPED"


def test_local_ci_references_canonical_generator() -> None:
    local_ci = (ROOT / "scripts/local-ci.sh").read_text()
    assert "scripts/validate-local-oauth.py" in local_ci
    assert "tests/test_oauth_local_generator.py" in local_ci
