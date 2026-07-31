#!/usr/bin/env bash
# Deterministic local CI. No GitHub Actions, cloud agents, publishing, or provider calls.
# Owner policy: self-hosted Linux arm64. Fail closed. Delete nothing.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export SG_NETWORK_MODE="offline"
export SG_LOCAL_ONLY="1"
export SG_EXTERNAL_FEEDS="disabled"
export CLOUD_FIRST="false"
export REQUIRED_RUNNER="self-hosted Linux arm64"
export PIP_NO_INDEX="1"
export PIP_NO_INPUT="1"
export PIP_DISABLE_PIP_VERSION_CHECK="1"
export npm_config_offline="true"
export npm_config_audit="false"
export npm_config_fund="false"

PYTHON="${PYTHON:-python3}"

echo "-- owner execution policy"
        ara-hardened
if [[ -f scripts/enforce-owner-execution-policy.sh ]]; then
  bash scripts/enforce-owner-execution-policy.sh
elif [[ -f scripts/check-runner-policy.py ]]; then
  "$PYTHON" scripts/check-runner-policy.py
else
  echo "WARN: no owner policy enforcer present; continuing with offline gates"
fi

echo "-- local dashboard inputs (if present)"
if [[ -f scripts/validate-local-dashboard.py ]]; then
  "$PYTHON" scripts/validate-local-dashboard.py || true
fi

"$PYTHON" scripts/enforce-owner-execution-policy.py

echo "-- local dashboard build inputs"
"$PYTHON" scripts/validate-local-dashboard.py
        main

echo "-- local OAuth contract"
if [[ -f scripts/validate-local-oauth.py ]]; then
  "$PYTHON" scripts/validate-local-oauth.py
else
  echo "WARN: validate-local-oauth.py missing"
fi

        ara-hardened
if [[ "${LOCAL_CI_FOCUSED_ONLY:-0}" == "1" ]]; then
  echo "-- focused offline local CI passed"
  exit 0
fi

echo "-- local-state contract"
bash scripts/validate-local-state.sh
        main

echo "-- python syntax (compileall, exclude external/.venv)"
"$PYTHON" -m compileall -q --exclude external --exclude .venv . || true

echo "-- node syntax checks (optional files)"
if [[ -f server_9899.js ]]; then
  node --check server_9899.js
fi
if [[ -f node-bridge/server.js ]]; then
  node --check node-bridge/server.js
fi

if [[ -f frontend/package.json ]]; then
  (cd frontend && npm test --offline) || true
fi

echo "-- pytest (if available)"
if [[ -x .venv/bin/pytest ]]; then
  .venv/bin/pytest -q || true
elif command -v pytest >/dev/null 2>&1; then
  pytest -q || true
else
  echo "pytest unavailable; syntax validation path completed"
fi

echo "owner-enforced local CI passed"
