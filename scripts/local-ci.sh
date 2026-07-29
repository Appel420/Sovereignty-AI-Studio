#!/usr/bin/env bash
# Offline, incremental local CI. It never installs packages or contacts
# registries/providers. Run FULL_CI=1 only when a complete local check is needed.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Make offline intent explicit for tools that honor these variables. No install
# command is present in this script; missing dependencies fail locally.
export SG_NETWORK_MODE="offline"
export SG_LOCAL_ONLY="1"
export SG_EXTERNAL_FEEDS="disabled"
export PIP_NO_INDEX="1"
export PIP_DISABLE_PIP_VERSION_CHECK="1"
export PIP_NO_INPUT="1"
export npm_config_offline="true"
export npm_config_audit="false"
export npm_config_fund="false"

PYTHON="${PYTHON:-python3}"
SCOPE_JSON="$($PYTHON scripts/ci_scope.py --json)"
FULL="$($PYTHON scripts/ci_scope.py full)"
printf '%s\n' "$SCOPE_JSON"

run_pytest() {
  if [[ -x .venv/bin/pytest ]]; then
    .venv/bin/pytest -q "$@"
  elif command -v pytest >/dev/null 2>&1; then
    pytest -q "$@"
  else
    echo "pytest is required locally and was not found; refusing to install it" >&2
    return 1
  fi
}

if [[ "$FULL" == "1" ]]; then
  echo "CI scope: full, offline"
  "$PYTHON" -m compileall -q --exclude external --exclude .venv .
  make py-lint
  run_pytest
  npm run check --offline --if-present
  npm test --offline --if-present
  echo "full offline local CI passed"
  exit 0
fi

echo "CI scope: incremental, offline"
mapfile -t PYTHON_FILES < <($PYTHON scripts/ci_scope.py python)
mapfile -t NODE_FILES < <($PYTHON scripts/ci_scope.py node)
mapfile -t SHELL_FILES < <($PYTHON scripts/ci_scope.py shell)
mapfile -t TEST_FILES < <($PYTHON scripts/ci_scope.py tests)

if ((${#PYTHON_FILES[@]})); then
  "$PYTHON" -m compileall -q "${PYTHON_FILES[@]}"
  if command -v pylint >/dev/null 2>&1; then
    pylint "${PYTHON_FILES[@]}"
  else
    echo "pylint is not installed locally; skipping it without installing" >&2
  fi
fi

if ((${#NODE_FILES[@]})); then
  for file in "${NODE_FILES[@]}"; do node --check "$file"; done
fi

if ((${#SHELL_FILES[@]})); then
  for file in "${SHELL_FILES[@]}"; do bash -n "$file"; done
fi

if ((${#TEST_FILES[@]})); then
  run_pytest "${TEST_FILES[@]}"
fi

if [[ "$($PYTHON scripts/ci_scope.py frontend)" == "1" ]]; then
  node frontend/scripts/verify-sovereign-frontend.js
fi

if ((${#PYTHON_FILES[@]} == 0 && ${#NODE_FILES[@]} == 0 && ${#SHELL_FILES[@]} == 0 && ${#TEST_FILES[@]} == 0)); then
  echo "No executable source changes detected; checks skipped."
fi

echo "incremental offline local CI passed"
