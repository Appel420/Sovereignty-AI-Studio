#!/usr/bin/env bash
# Incremental local CI. Full validation is reserved for dependency, workflow,
# build, runtime-map changes, or an explicit FULL_CI=1.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
SCOPE_JSON="$($PYTHON scripts/ci_scope.py --json)"
FULL="$($PYTHON scripts/ci_scope.py full)"

printf '%s\n' "$SCOPE_JSON"

if [[ "$FULL" == "1" ]]; then
  echo "CI scope: full (dependency, workflow, build, or explicit FULL_CI change)"
  "$PYTHON" -m compileall -q --exclude external --exclude .venv .
  make py-lint
  if [[ -x .venv/bin/pytest ]]; then
    .venv/bin/pytest -q
  else
    "$PYTHON" -m pytest -q
  fi
  npm run check
  npm test --if-present
  echo "full local CI passed"
  exit 0
fi

echo "CI scope: incremental"

mapfile -t PYTHON_FILES < <($PYTHON scripts/ci_scope.py python)
mapfile -t NODE_FILES < <($PYTHON scripts/ci_scope.py node)
mapfile -t SHELL_FILES < <($PYTHON scripts/ci_scope.py shell)
mapfile -t TEST_FILES < <($PYTHON scripts/ci_scope.py tests)

if ((${#PYTHON_FILES[@]})); then
  echo "Checking changed Python files"
  "$PYTHON" -m compileall -q "${PYTHON_FILES[@]}"
  if command -v pylint >/dev/null 2>&1; then
    pylint "${PYTHON_FILES[@]}"
  fi
fi

if ((${#NODE_FILES[@]})); then
  echo "Checking changed Node files"
  for file in "${NODE_FILES[@]}"; do
    node --check "$file"
  done
fi

if ((${#SHELL_FILES[@]})); then
  echo "Checking changed shell files"
  for file in "${SHELL_FILES[@]}"; do
    bash -n "$file"
  done
fi

if ((${#TEST_FILES[@]})); then
  echo "Running changed Python tests only"
  if [[ -x .venv/bin/pytest ]]; then
    .venv/bin/pytest -q "${TEST_FILES[@]}"
  else
    "$PYTHON" -m pytest -q "${TEST_FILES[@]}"
  fi
fi

if [[ "$($PYTHON scripts/ci_scope.py frontend)" == "1" ]]; then
  echo "Running frontend verification"
  node frontend/scripts/verify-sovereign-frontend.js
fi

if ((${#PYTHON_FILES[@]} == 0 && ${#NODE_FILES[@]} == 0 && ${#SHELL_FILES[@]} == 0 && ${#TEST_FILES[@]} == 0)); then
  echo "No executable source changes detected; source checks skipped."
fi

echo "incremental local CI passed"
