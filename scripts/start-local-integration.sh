#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

python3 "$ROOT_DIR/scripts/local_integration.py" check

if [[ "${SOVEREIGNTY_START_SERVICES:-1}" != "1" ]]; then
  echo "preflight passed; service startup disabled by SOVEREIGNTY_START_SERVICES"
  exit 0
fi

if [[ ! -x "$ROOT_DIR/START_SERVER.sh" ]]; then
  echo "preflight passed, but START_SERVER.sh is unavailable or not executable" >&2
  echo "No service was started." >&2
  exit 1
fi

exec "$ROOT_DIR/START_SERVER.sh"
