#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORT_DIR="automation/reports"
mkdir -p "$REPORT_DIR"

echo "== SGHV119 Local CI =="
echo "Root: $ROOT_DIR"
echo

run_optional() {
  local label="$1"
  shift
  echo "-- $label"
  if command -v "$1" >/dev/null 2>&1; then
    "$@"
  else
    echo "skip: command not found: $1"
  fi
  echo
}

# 1. Repository sanitization and architecture inventory.
echo "-- sanitize audit"
if python3 scripts/sg_sanitize_audit.py; then
  echo "sanitize audit: clean"
else
  echo "sanitize audit: findings generated; review $REPORT_DIR/sanitization_findings.json"
fi
echo

# 2. Local OAuth generator hook. This is intentionally local-only.
# Set LOCAL_OAUTH_GENERATOR to your local script path if it differs.
LOCAL_OAUTH_GENERATOR="${LOCAL_OAUTH_GENERATOR:-scripts/oauth-local-generator.sh}"
echo "-- local OAuth generator"
if [[ -x "$LOCAL_OAUTH_GENERATOR" ]]; then
  "$LOCAL_OAUTH_GENERATOR" --dry-run --report "$REPORT_DIR/oauth-local-report.json" || true
else
  echo "skip: no executable local OAuth generator at $LOCAL_OAUTH_GENERATOR"
  echo "{\"status\":\"skipped\",\"reason\":\"local OAuth generator not configured\"}" > "$REPORT_DIR/oauth-local-report.json"
fi
echo

# 3. SBOM hook. Prefer local tools. Do not call SaaS scanners by default.
echo "-- SBOM"
if command -v syft >/dev/null 2>&1; then
  syft dir:. -o spdx-json > "$REPORT_DIR/sbom.spdx.json"
  echo "sbom: generated with syft"
elif [[ -x scripts/generate-sbom.sh ]]; then
  scripts/generate-sbom.sh "$REPORT_DIR/sbom.spdx.json" || true
else
  echo "skip: syft not found and scripts/generate-sbom.sh not executable"
  echo "{\"status\":\"skipped\",\"reason\":\"no local SBOM generator configured\"}" > "$REPORT_DIR/sbom.spdx.json"
fi
echo

# 4. Lightweight local checks. Keep them offline/local.
run_optional "python syntax check" python3 -m compileall -q scripts backend ai_core . 2>/dev/null || true

if [[ -f node-bridge/package.json ]]; then
  echo "-- node bridge package check"
  node -e "JSON.parse(require('fs').readFileSync('node-bridge/package.json','utf8')); console.log('node-bridge/package.json ok')" || true
  echo
fi

# 5. Summary.
echo "== Summary =="
if [[ -f "$REPORT_DIR/summary.json" ]]; then
  cat "$REPORT_DIR/summary.json"
else
  echo "summary missing"
fi

echo
echo "Reports: $REPORT_DIR"
echo "Local CI complete. Review reports before committing generated artifacts."
