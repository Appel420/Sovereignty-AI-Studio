#!/usr/bin/env bash
# Deterministic local CI. No GitHub Actions, cloud agents, or provider calls.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m compileall -q --exclude external --exclude .venv .
node --check server_9899.js
node --check node-bridge/server.js

if [[ -f frontend/package.json ]]; then
  (cd frontend && npm test)
fi

if [[ -x .venv/bin/pytest ]]; then
  .venv/bin/pytest -q
elif command -v pytest >/dev/null 2>&1; then
  pytest -q
else
  echo "pytest unavailable; Python syntax validation passed"
fi

echo "local CI passed"
