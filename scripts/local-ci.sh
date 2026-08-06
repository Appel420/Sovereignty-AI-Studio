#!/usr/bin/env bash
# Authoritative device-local CI. No package installation, provider calls,
# external OAuth, cloud fallback, or synthetic production evidence.
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

run_required "$PYTHON" scripts/verify_ci_policy.py
run_required "$PYTHON" scripts/security_policy_scan.py ZERO_TOLERANCE_POLICY.json .
run_required "$PYTHON" scripts/check-runner-policy.py
run_required "$PYTHON" scripts/enforce-owner-execution-policy.py
run_required "$PYTHON" scripts/validate-local-dashboard.py
run_required "$PYTHON" scripts/validate-local-oauth.py
run_required "$PYTHON" scripts/audit-external-integrations.py
run_required "$PYTHON" scripts/validate-php-ios-environment.py

if [[ "${LOCAL_CI_FOCUSED_ONLY:-0}" == "1" ]]; then
  echo "focused offline local CI passed; production attestation not performed"
  exit 0
fi

if [[ -f scripts/validate-local-state.sh ]]; then
  run_required bash scripts/validate-local-state.sh
fi

run_required "$PYTHON" -m compileall -q --exclude external --exclude .venv .

if command -v node >/dev/null 2>&1; then
  [[ -f server_9899.js ]] && run_required node --check server_9899.js
  [[ -f node-bridge/server.js ]] && run_required node --check node-bridge/server.js
fi

if command -v php >/dev/null 2>&1; then
  run_required php -l scripts/php_local_bootstrap.php
fi

if [[ -x .venv/bin/pytest ]]; then
  run_required .venv/bin/pytest -q
elif command -v pytest >/dev/null 2>&1; then
  run_required pytest -q
else
  echo "BLOCKED: pytest unavailable; no packages will be installed"
  exit 2
fi

exec "$PYTHON" scripts/run-local-ci.py --ci-name coordination-unit-ci-local "$@"
