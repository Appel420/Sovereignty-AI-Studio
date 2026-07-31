#!/usr/bin/env bash
# Owner execution policy gate. Fail closed. Delete nothing.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export SG_NETWORK_MODE="${SG_NETWORK_MODE:-offline}"
export SG_LOCAL_ONLY="${SG_LOCAL_ONLY:-1}"
export SG_EXTERNAL_FEEDS="${SG_EXTERNAL_FEEDS:-disabled}"
export CLOUD_FIRST="${CLOUD_FIRST:-false}"
export REQUIRED_RUNNER="${REQUIRED_RUNNER:-self-hosted Linux arm64}"

POLICY="config/owner-execution-policy.json"
FAILED=0

echo "-- owner execution policy"

if [[ ! -f "$POLICY" ]]; then
  echo "MISSING: $POLICY" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' || exit 1
import json, sys
from pathlib import Path
p = Path("config/owner-execution-policy.json")
data = json.loads(p.read_text(encoding="utf-8"))
errors = []
if data.get("cloud_allowed") is not False:
    errors.append("cloud_allowed must be false")
if data.get("cloud_first") is not False:
    errors.append("cloud_first must be false")
if data.get("fail_closed") is not True:
    errors.append("fail_closed must be true")
if data.get("delete_nothing") is not True:
    errors.append("delete_nothing must be true")
req = data.get("required_runner")
if req != ["self-hosted Linux arm64"]:
    errors.append(f"required_runner must be [\"self-hosted Linux arm64\"], got {req!r}")
if errors:
    for e in errors:
        print(f"POLICY FAIL: {e}", file=sys.stderr)
    sys.exit(1)
print("policy file OK")
PY
else
  echo "python3 required for policy validation" >&2
  exit 1
fi

echo "-- workflow runner scan"
if [[ -x scripts/check-runner-policy.py ]]; then
  python3 scripts/check-runner-policy.py || FAILED=1
elif [[ -f scripts/check-runner-policy.py ]]; then
  python3 scripts/check-runner-policy.py || FAILED=1
else
  # Inline fallback — same rule, no deletion
  while IFS= read -r line; do
    file="${line%%:*}"
    rest="${line#*:}"
    value="$(echo "$rest" | sed -n 's/.*runs-on:[[:space:]]*//p' | head -1)"
    if [[ -n "$value" && "$value" != "['self-hosted Linux arm64']" ]]; then
      echo "INVALID RUNNER: $file: $value" >&2
      FAILED=1
    fi
  done < <(grep -RInE 'runs-on:' .github/workflows --include='*.yml' --include='*.yaml' 2>/dev/null || true)
fi

if [[ "$CLOUD_FIRST" == "true" ]]; then
  echo "CLOUD_FIRST=true is prohibited" >&2
  FAILED=1
fi

if [[ "$FAILED" -ne 0 ]]; then
  echo "owner execution policy FAILED (fail closed)" >&2
  exit 1
fi

echo "owner execution policy passed"
