"""README governance invariants."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_OPENING_RULE = (
    "This is the main dedicated branch. All changes by Claude Grok/Ara DuckAI "
    "GPT/Codex Copilot must be made in their dedicated branch. Do not push "
    "directly to main. Create a Pull Request for review."
)


def test_readme_preserves_opening_branch_rule() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lines = [line.strip() for line in readme.splitlines() if line.strip()]
    assert EXPECTED_OPENING_RULE in lines[:5]


def test_readme_documents_three_runtime_modes() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for term in ("LOCAL", "HYBRID", "ONLINE", "PHPWin"):
        assert term in readme


def test_readme_documents_artifact_classes() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for term in ("canonical", "derived", "external"):
        assert term in readme
