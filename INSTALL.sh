#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OFFLINE=0

if [[ "${1:-}" == "--offline" ]]; then
  OFFLINE=1
elif [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--offline]" >&2
  exit 64
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: Python 3.11 or newer is required." >&2
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: Node.js 20 or newer and npm are required." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("ERROR: Python 3.11 or newer is required.")
PY

NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]")"
if (( NODE_MAJOR < 20 )); then
  echo "ERROR: Node.js 20 or newer is required." >&2
  exit 1
fi

cd "$SCRIPT_DIR"
if [[ ! -f requirements-runtime.txt ]]; then
  echo "ERROR: requirements-runtime.txt is missing from the repository root." >&2
  exit 1
fi
if [[ ! -f package-lock.json || ! -f node-bridge/package-lock.json ]]; then
  echo "ERROR: npm lockfiles are required for deterministic installation." >&2
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

PIP_ARGS=()
NPM_ARGS=()
if (( OFFLINE )); then
  PIP_ARGS+=(--no-index)
  NPM_ARGS+=(--offline)
else
  "$VENV_PYTHON" -m pip install --upgrade pip
fi

"$VENV_PYTHON" -m pip install "${PIP_ARGS[@]}" -r requirements-runtime.txt
npm ci "${NPM_ARGS[@]}" --ignore-scripts
npm --prefix node-bridge ci "${NPM_ARGS[@]}" --ignore-scripts

"$VENV_PYTHON" - <<'PY'
import websockets
print(f"Python runtime dependencies verified (websockets {websockets.__version__})")
PY
node --check node-bridge/server.js
echo "Installation complete. Configure only an approved local inference provider, then run ./START_SERVER.sh."
