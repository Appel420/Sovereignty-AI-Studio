#!/usr/bin/env python3
"""Auto-regenerate README implementation status block from current repository state."""

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
    # === Core tracked implementation files ===
    tracked_files = [
        repo_root / "fixers/database_fixer.py",
        repo_root / "tests/test_fixers.py",
        repo_root / ".github/workflows/ci.yml",
        repo_root / ".github/workflows/oauth-api-generator.yml",
        repo_root / ".github/workflows/readme-implementation-sync.yml",
        repo_root / "SGHv119.html",                    # Dashboard + Live Terminal + Package Installer
    ]

    existing = [f for f in tracked_files if f.exists()]

    fingerprint = hashlib.sha256(
        "".join(_file_hash(f) for f in existing).encode("utf-8")
    ).hexdigest()[:16]

    # Behavioral checks
    db_fixer_text = ""
    db_fixer_path = repo_root / "fixers/database_fixer.py"
    if db_fixer_path.exists():
        db_fixer_text = db_fixer_path.read_text(encoding="utf-8")

    has_parent_mkdir = "self.db_path.parent.mkdir(parents=True, exist_ok=True)" in db_fixer_text

    return f"""{START_MARKER}
## Implementation Status (Auto-Generated)

- **Implementation fingerprint:** `{fingerprint}`
- **Last regenerated:** by `update_readme_implementation.py`

### Tracked Files
{chr(10).join(f"- `{f.relative_to(repo_root)}` (`{_short_hash(f)}` )" for f in existing)}

### Key Behaviors Detected
- Database fixer creates parent directories before rebuild: {"✅ enabled" if has_parent_mkdir else "❌ not detected"}

### Architecture Notes
- Frontend served on **port 9898**
- All backend / WebSocket traffic routes through **port 9899** (node-bridge gateway)
- Dashboard + Live Terminal with package installer integrated in `SGHv119.html`
- README implementation status is self-updating via GitHub Actions
{END_MARKER}
"""


def _last_updated_label(repo_root: Path, tracked_files: list[Path]) -> str | None:
    relative = [str(p.relative_to(repo_root)) for p in tracked_files]
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%cs", "--", *relative],
            check=True, capture_output=True, text=True
        )
        date_str = result.stdout.strip()
        if not date_str:
            return None
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")
    except Exception:
        return None


def update_readme(repo_root: Path) -> bool:
    readme_path = repo_root / "README.md"
    if not readme_path.exists():
        return False

    readme_text = readme_path.read_text(encoding="utf-8")
    generated = build_section(repo_root)

    if START_MARKER in readme_text and END_MARKER in readme_text:
        start = readme_text.index(START_MARKER)
        end = readme_text.index(END_MARKER) + len(END_MARKER)
        updated = readme_text[:start] + generated + readme_text[end:]
    else:
        anchor = "\n## Features\n"
        if anchor in readme_text:
            updated = readme_text.replace(anchor, f"\n{generated}\n## Features\n", 1)
        else:
            updated = readme_text.rstrip() + "\n\n" + generated + "\n"

    # Update "Last Updated" date
    last_updated = _last_updated_label(repo_root, [
        repo_root / "fixers/database_fixer.py",
        repo_root / "tests/test_fixers.py",
    ])
    if last_updated:
        updated = re.sub(
            r"\*\*Last Updated:\*\* .+",
            f"**Last Updated:** {last_updated}",
            updated,
            count=1
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
