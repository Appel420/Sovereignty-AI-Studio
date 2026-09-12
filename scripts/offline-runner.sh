#!/usr/bin/env bash
# Sovereignty-AI-Studio offline runner.
# Runs the local build/test surface without GitHub Actions, hosted runners,
# dependency installation, network access, artifact upload, or git push.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_NAME="${OFFLINE_CI_NAME:-sovereignty-offline-ci}"
REPORT_DIR="${OFFLINE_CI_REPORT_DIR:-$ROOT_DIR/reports}"
LOG_DIR="${OFFLINE_CI_LOG_DIR:-$ROOT_DIR/reports/logs}"
LOCK_FILE="${OFFLINE_CI_LOCK:-$ROOT_DIR/.offline-ci.lock}"
START_SERVICES="${OFFLINE_CI_START_SERVICES:-0}"

mkdir -p "$REPORT_DIR" "$LOG_DIR"

if ! (set -o noclobber; : > "$LOCK_FILE") 2>/dev/null; then
  echo "BLOCKED: offline CI is already running (lock: $LOCK_FILE)" >&2
  exit 2
fi
cleanup() { rm -f "$LOCK_FILE"; }
trap cleanup EXIT INT TERM

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/${RUN_NAME}-${STAMP}.log"
REPORT_FILE="$REPORT_DIR/${RUN_NAME}-${STAMP}.json"
exec > >(tee -a "$LOG_FILE") 2>&1

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SHA="$(git rev-parse HEAD 2>/dev/null || printf 'unknown')"
BRANCH="$(git branch --show-current 2>/dev/null || printf 'unknown')"

printf '%s\n' '============================================================'
printf 'OFFLINE CI: %s\n' "$RUN_NAME"
printf 'MODE: LOCAL/OFFLINE\n'
printf 'CLOUD: NOT USED\n'
printf 'BRANCH: %s\n' "$BRANCH"
printf 'COMMIT: %s\n' "$SHA"
printf '%s\n' '============================================================'

export SG_NETWORK_MODE="offline"
export SG_LOCAL_ONLY="1"
export SG_EXTERNAL_FEEDS="disabled"
export CLOUD_FIRST="false"
export PIP_NO_INDEX="1"
export PIP_NO_INPUT="1"
export PIP_DISABLE_PIP_VERSION_CHECK="1"
export npm_config_offline="true"
export npm_config_audit="false"
export npm_config_fund="false"
export NO_PROXY="*"
export no_proxy="*"

results=()
failed=0
run_check() {
  local name="$1"; shift
  printf '\n-- %s\n' "$name"
  if "$@"; then
    results+=("{\"name\":\"$name\",\"status\":\"PASS\"}")
  else
    local code=$?
    results+=("{\"name\":\"$name\",\"status\":\"FAIL\",\"exit\":$code}")
    failed=1
  fi
}

run_check "shell-syntax" bash -n scripts/local-ci.sh scripts/enforce-owner-execution-policy.sh

if [[ -f frontend/runtime/hawking-runtime.js && -f frontend/runtime/test-hawking-runtime.test.js ]]; then
  run_check "hawking-runtime" bash frontend/runtime/test-hawking-runtime.sh
fi

if [[ -f frontend/runtime/hawking-channel.js && -f frontend/runtime/test-hawking-channel.js ]]; then
  run_check "hawking-channel" node frontend/runtime/test-hawking-channel.js
fi

if [[ -f scripts/validate-runtime-coherence.py ]]; then
  run_check "runtime-coherence" python3 scripts/validate-runtime-coherence.py
fi

if [[ -f scripts/validate-local-state.sh ]]; then
  run_check "local-state" bash scripts/validate-local-state.sh
fi

run_check "canonical-local-ci" bash scripts/local-ci.sh --ci-name ara-hardened-unit-ci-local --why "offline runner validation"

if [[ "$START_SERVICES" == "1" ]]; then
  if [[ -x START_SERVER.sh ]]; then
    printf '\n-- start-services\n'
    exec ./START_SERVER.sh
  else
    echo "FAIL: OFFLINE_CI_START_SERVICES=1 requested but START_SERVER.sh is unavailable or not executable" >&2
    failed=1
  fi
fi

COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RESULTS_JSON="[$(IFS=,; echo "${results[*]}")]"
python3 - "$REPORT_FILE" "$RUN_NAME" "$BRANCH" "$SHA" "$STARTED_AT" "$COMPLETED_AT" "$LOG_FILE" "$failed" "$RESULTS_JSON" <<'PY'
import json, pathlib, sys
(path, name, branch, sha, started, completed, log, failed, results) = sys.argv[1:]
data = {
    "ci_name": name,
    "mode": "local",
    "network": "disabled",
    "cloud": "not_used",
    "branch": branch,
    "commit": sha,
    "started_at": started,
    "completed_at": completed,
    "log": log,
    "status": "FAIL" if failed != "0" else "PASS",
    "results": json.loads(results),
}
pathlib.Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(json.dumps(data, indent=2))
PY

printf '\nreport: %s\n' "$REPORT_FILE"
printf 'log: %s\n' "$LOG_FILE"
exit "$failed"
