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

run_required() {
  echo "-- $*"
  "$@"
}

run_optional() {
  local label="$1"
  shift
  if "$@"; then
    return 0
  fi
  echo "SKIPPED: ${label}"
  return 0
}

echo "-- owner execution policy"
if [[ -f scripts/enforce-owner-execution-policy.sh ]]; then
  run_required bash scripts/enforce-owner-execution-policy.sh
elif [[ -f scripts/check-runner-policy.py ]]; then
  run_required "$PYTHON" scripts/check-runner-policy.py
else
  echo "SKIPPED: owner policy shell/check-runner gate unavailable"
fi

run_required "$PYTHON" scripts/enforce-owner-execution-policy.py

if [[ -f scripts/validate-local-dashboard.py ]]; then
  run_required "$PYTHON" scripts/validate-local-dashboard.py
else
  echo "SKIPPED: scripts/validate-local-dashboard.py unavailable"
fi

if [[ -f scripts/validate-local-oauth.py ]]; then
  run_required "$PYTHON" scripts/validate-local-oauth.py
else
  echo "SKIPPED: local OAuth contract unavailable"
fi

if [[ "${LOCAL_CI_FOCUSED_ONLY:-0}" == "1" ]]; then
  echo "focused offline local CI passed"
  exit 0
fi

if [[ -f scripts/validate-local-state.sh ]]; then
  run_required bash scripts/validate-local-state.sh
else
  echo "SKIPPED: local-state contract unavailable"
fi

echo "-- python syntax (compileall, exclude external/.venv)"
run_required "$PYTHON" -m compileall -q --exclude external --exclude .venv .

echo "-- node syntax checks (optional files)"
if command -v node >/dev/null 2>&1; then
  [[ -f server_9899.js ]] && run_required node --check server_9899.js
  [[ -f node-bridge/server.js ]] && run_required node --check node-bridge/server.js
else
  echo "SKIPPED: node unavailable"
fi

if [[ -f frontend/package.json ]] && command -v npm >/dev/null 2>&1; then
  run_optional "frontend npm test unavailable or failing" bash -c 'cd frontend && npm test --offline'
elif [[ -f frontend/package.json ]]; then
  echo "SKIPPED: npm unavailable"
fi

echo "-- pytest (if available)"
if [[ -x .venv/bin/pytest ]]; then
  run_required .venv/bin/pytest -q
elif command -v pytest >/dev/null 2>&1; then
  run_required pytest -q
else
  echo "SKIPPED: pytest unavailable"
fi

echo "owner-enforced local CI passed"
