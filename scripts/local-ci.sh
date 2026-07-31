#!/usr/bin/env bash
# Deterministic local CI. No GitHub Actions, cloud agents, publishing, or provider calls.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export SG_NETWORK_MODE="offline"
export SG_LOCAL_ONLY="1"
export SG_EXTERNAL_FEEDS="disabled"
export PIP_NO_INDEX="1"
export PIP_NO_INPUT="1"
export PIP_DISABLE_PIP_VERSION_CHECK="1"
export npm_config_offline="true"
export npm_config_audit="false"
export npm_config_fund="false"

PYTHON="${PYTHON:-python3}"

echo "-- owner execution policy"
"$PYTHON" scripts/enforce-owner-execution-policy.py

echo "-- local dashboard build inputs"
"$PYTHON" scripts/validate-local-dashboard.py

echo "-- local OAuth contract"
"$PYTHON" scripts/validate-local-oauth.py

echo "-- local-state contract"
bash scripts/validate-local-state.sh

python3 -m compileall -q --exclude external --exclude .venv .
node --check server_9899.js
node --check node-bridge/server.js

if [[ -f frontend/package.json ]]; then
  (cd frontend && npm test --offline)
fi

if [[ -x .venv/bin/pytest ]]; then
  .venv/bin/pytest -q
elif command -v pytest >/dev/null 2>&1; then
  pytest -q
else
  echo "pytest unavailable; Python syntax validation passed" >&2
fi

echo "owner-enforced local CI passed"
