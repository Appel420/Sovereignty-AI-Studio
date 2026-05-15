#!/usr/bin/env python3
"""Regenerate README implementation status block from current repository state."""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime
from pathlib import Path

START_MARKER = "<!-- BEGIN:IMPLEMENTATION_STATUS -->"
END_MARKER = "<!-- END:IMPLEMENTATION_STATUS -->"


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _short_hash(path: Path) -> str:
    return _file_hash(path)[:12]


def build_section(repo_root: Path) -> str:
    db_fixer_path = repo_root / "fixers/database_fixer.py"
    fixer_tests_path = repo_root / "tests/test_fixers.py"
    ci_workflow_path = repo_root / ".github/workflows/ci.yml"
    oauth_workflow_path = repo_root / ".github/workflows/oauth-api-generator.yml"

    db_fixer_text = db_fixer_path.read_text(encoding="utf-8")
    fixer_tests_text = fixer_tests_path.read_text(encoding="utf-8")
    ci_workflow_text = ci_workflow_path.read_text(encoding="utf-8")
    oauth_workflow_text = oauth_workflow_path.read_text(encoding="utf-8")

    tracked_files = [
        db_fixer_path,
        fixer_tests_path,
        ci_workflow_path,
        oauth_workflow_path,
    ]
    fingerprint = hashlib.sha256(
        "".join(_file_hash(path) for path in tracked_files).encode("utf-8")
    ).hexdigest()[:16]

    has_parent_mkdir = "self.db_path.parent.mkdir(parents=True, exist_ok=True)" in db_fixer_text
    has_schema_exec = "conn.executescript(self.schema)" in db_fixer_text
    has_required_tables = all(
        table in db_fixer_text for table in ("conversations", "kv", "events")
    )
    has_integrity_assertions = (
        "assert is_healthy is True" in fixer_tests_text
        and "assert issues == []" in fixer_tests_text
    )
    ci_runs_pytest = "pytest --cov=apps --cov=backend --cov=src" in ci_workflow_text
    oauth_runs_pytest = "pytest --cov=apps --cov=backend --cov=src" in oauth_workflow_text
    ci_uses_workflow_requirements = (
        "pip install -r .github/workflows/Requirements.txt" in ci_workflow_text
        and "pip install -r .github/workflows/Requirements.txt" in oauth_workflow_text
    )

    return f"""{START_MARKER}
## Implementation Status (Auto-Generated)

- **Implementation fingerprint:** `{fingerprint}`
- **DatabaseFixer source:** `fixers/database_fixer.py` (`{_short_hash(db_fixer_path)}`)
- **Regression test source:** `tests/test_fixers.py` (`{_short_hash(fixer_tests_path)}`)

### Database fixer behavior
- Parent-directory creation before rebuild: {"enabled" if has_parent_mkdir else "not detected"}
- Schema execution during rebuild: {"enabled" if has_schema_exec else "not detected"}
- Required integrity tables ensured (`conversations`, `kv`, `events`): {"enabled" if has_required_tables else "not detected"}

### Fixer regression coverage
- `TestDatabaseFixer.test_rebuild_database` validates rebuild success and clean integrity issues: {"enabled" if has_integrity_assertions else "not detected"}

### CI workflow alignment
- `.github/workflows/ci.yml` runs pytest coverage for implementation code: {"enabled" if ci_runs_pytest else "not detected"}
- `.github/workflows/oauth-api-generator.yml` runs pytest coverage for implementation code: {"enabled" if oauth_runs_pytest else "not detected"}
- Both workflows install `.github/workflows/Requirements.txt`: {"enabled" if ci_uses_workflow_requirements else "not detected"}
- README auto-sync workflow: `.github/workflows/readme-implementation-sync.yml`
{END_MARKER}
"""


def _last_updated_label(repo_root: Path, tracked_files: list[Path]) -> str | None:
    relative_files = [str(path.relative_to(repo_root)) for path in tracked_files]
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%cs", "--", *relative_files],
            check=True,
            capture_output=True,
            text=True,
        )
        date_str = result.stdout.strip()
        if not date_str:
            return None
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    except Exception:
        return None


def update_readme(repo_root: Path) -> bool:
    tracked_files = [
        repo_root / "fixers/database_fixer.py",
        repo_root / "tests/test_fixers.py",
        repo_root / ".github/workflows/ci.yml",
        repo_root / ".github/workflows/oauth-api-generator.yml",
    ]
    readme_path = repo_root / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")
    generated = build_section(repo_root)

    if START_MARKER in readme_text and END_MARKER in readme_text:
        start = readme_text.index(START_MARKER)
        end = readme_text.index(END_MARKER) + len(END_MARKER)
        while end < len(readme_text) and readme_text[end] == "\n":
            end += 1
        updated = (
            readme_text[:start].rstrip()
            + "\n\n"
            + generated.strip()
            + "\n\n"
            + readme_text[end:].lstrip("\n")
        )
    else:
        anchor = "\n## Features\n"
        if anchor in readme_text:
            updated = readme_text.replace(
                anchor, f"\n\n{generated.strip()}\n\n## Features\n", 1
            )
        else:
            updated = readme_text.rstrip() + "\n\n" + generated.strip() + "\n"

    last_updated = _last_updated_label(repo_root, tracked_files)
    if last_updated:
        updated = re.sub(
            r"\*\*Last Updated:\*\* .+",
            f"**Last Updated:** {last_updated}",
            updated,
            count=1,
        )

    if updated == readme_text:
        return False

    readme_path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    changed = update_readme(repo_root)
    print("README updated" if changed else "README already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
