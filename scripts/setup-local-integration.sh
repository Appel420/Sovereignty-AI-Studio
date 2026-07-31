#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
MANIFEST="$ROOT_DIR/integration/local-repositories.json"
WORKSPACE="${SOVEREIGNTY_WORKSPACE:-$HOME/Sovereignty}"

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

mkdir -p "$WORKSPACE"

python3 - "$MANIFEST" "$WORKSPACE" <<'PY'
import json
import pathlib
import subprocess
import sys

manifest_path = pathlib.Path(sys.argv[1])
workspace = pathlib.Path(sys.argv[2]).expanduser()
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

for repository in manifest["repositories"]:
    target = workspace / repository["relative_path"]
    if (target / ".git").exists():
        print(f"exists: {target}")
        continue
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"refusing non-empty non-git directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"clone: {repository['name']} -> {target}")
    subprocess.run(["git", "clone", repository["remote"], str(target)], check=True)
PY

printf '\nLocal checkouts prepared at %s\n' "$WORKSPACE"
printf 'Run the offline preflight with:\n  SOVEREIGNTY_WORKSPACE=%q python3 %q check\n' "$WORKSPACE" "$ROOT_DIR/scripts/local_integration.py"
