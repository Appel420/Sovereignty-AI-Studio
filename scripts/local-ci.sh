#!/usr/bin/env bash
# Authoritative local CI. Network mode is explicit: offline, hybrid, or online.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

NETWORK_MODE="${SG_NETWORK_MODE:-offline}"
case "$NETWORK_MODE" in
  offline|hybrid|online) ;;
  *) echo "BLOCKED: SG_NETWORK_MODE must be offline, hybrid, or online" >&2; exit 2 ;;
esac

export SG_NETWORK_MODE="$NETWORK_MODE"
export SG_LOCAL_ONLY="${SG_LOCAL_ONLY:-$([[ "$NETWORK_MODE" == offline ]] && echo 1 || echo 0)}"
export SG_EXTERNAL_FEEDS="${SG_EXTERNAL_FEEDS:-$([[ "$NETWORK_MODE" == online ]] && echo enabled || echo disabled)}"
export CLOUD_FIRST="${CLOUD_FIRST:-false}"
export REQUIRED_RUNNER="self-hosted Linux arm64"
export PIP_NO_INPUT="${PIP_NO_INPUT:-1}"
export PIP_DISABLE_PIP_VERSION_CHECK="${PIP_DISABLE_PIP_VERSION_CHECK:-1}"

if [[ "$NETWORK_MODE" == offline ]]; then
  export PIP_NO_INDEX="1"
  export npm_config_offline="true"
else
  unset PIP_NO_INDEX || true
  export npm_config_offline="false"
fi
export npm_config_audit="${npm_config_audit:-false}"
export npm_config_fund="${npm_config_fund:-false}"

echo "CI network mode: $NETWORK_MODE"
run_required() { echo "-- $*"; "$@"; }

run_required "$PYTHON" scripts/verify_ci_policy.py
run_required "$PYTHON" scripts/security_policy_scan.py ZERO_TOLERANCE_POLICY.json .
run_required "$PYTHON" scripts/check-runner-policy.py
run_required "$PYTHON" scripts/enforce-owner-execution-policy.py
run_required "$PYTHON" scripts/validate-local-dashboard.py
run_required "$PYTHON" scripts/validate-local-oauth.py
run_required "$PYTHON" scripts/audit-external-integrations.py
run_required "$PYTHON" scripts/validate-php-ios-environment.py

if [[ "${LOCAL_CI_FOCUSED_ONLY:-0}" == "1" ]]; then
  echo "focused $NETWORK_MODE CI passed; production attestation not performed"
  exit 0
fi

if [[ -f scripts/validate-local-state.sh ]]; then
  run_required bash scripts/validate-local-state.sh
fi
run_required "$PYTHON" -m compileall -q --exclude external --exclude .venv .

if command -v cargo >/dev/null 2>&1 && [[ -f Cargo.toml ]]; then
  [[ "$NETWORK_MODE" == offline ]] && run_required cargo test --workspace --offline || run_required cargo test --workspace
fi
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
  echo "BLOCKED: pytest unavailable; install dependencies for $NETWORK_MODE mode before running CI" >&2
  exit 2
fi
exec "$PYTHON" scripts/run-local-ci.py --ci-name coordination-unit-ci-local "$@"
