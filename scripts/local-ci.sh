#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORT_DIR="automation/reports"
mkdir -p "$REPORT_DIR"

echo "== SGHV119 Local CI =="
echo "Root: $ROOT_DIR"
echo

# 1. Minimal Guardian. PLATFORM.json is the policy source.
echo "-- Guardian Genesis-0-1"
GUARDIAN_STATUS=0
if python3 scripts/guardian_minimal.py; then
  echo "guardian: clean or warnings only"
else
  GUARDIAN_STATUS=$?
  echo "guardian: blocking findings generated; review $REPORT_DIR/guardian-findings.json"
fi
echo

# 2. Offline inventory. This is cave-mode safe: local files only, no network.
echo "-- offline inventory"
if python3 scripts/offline_inventory.py; then
  echo "offline inventory: reports generated"
else
  echo "offline inventory: failed; review script locally"
fi
echo

# 3. Repository sanitization and architecture inventory.
echo "-- sanitize audit"
if python3 scripts/sg_sanitize_audit.py; then
  echo "sanitize audit: clean"
else
  echo "sanitize audit: findings generated; review $REPORT_DIR/sanitization_findings.json"
fi
echo

# 4. Run the repository-owned OAuth generator without any remote provider.
echo "-- local OAuth generator"
python3 scripts/oauth_local_generator.py --dry-run --report "$REPORT_DIR/oauth-local-report.json"
echo

# 5. SBOM hook. Prefer local tools. Do not call SaaS scanners by default.
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

# 6. Actual project checks. These commands do not install packages or contact
# external services, so missing local dependencies are a failure rather than a
# successful-looking skip.
echo "-- Python syntax check"
python3 -m compileall -q scripts backend ai_core
echo

echo "-- Node syntax check"
npm run check
echo

echo "-- Sovereign memory vault tests"
node tests/test_sovereign_memory_vault.js
echo

echo "-- Local control-plane tests"
python3 -m pytest tests/test_local_control_plane.py
echo

if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "-- iPhone package build"
  swift build --package-path ios
  echo
else
  echo "-- iPhone package build"
  echo "not run: iPhone validation requires macOS with Xcode; run this local CI on the iPhone build host."
  echo
fi

# 7. Summary.
echo "== Guardian Summary =="
if [[ -f "$REPORT_DIR/guardian-summary.json" ]]; then
  cat "$REPORT_DIR/guardian-summary.json"
else
  echo "guardian summary missing"
fi

echo
echo "== Offline Inventory Summary =="
if [[ -f "$REPORT_DIR/offline-inventory-summary.json" ]]; then
  cat "$REPORT_DIR/offline-inventory-summary.json"
else
  echo "offline inventory summary missing"
fi

echo
echo "== Sanitize Summary =="
if [[ -f "$REPORT_DIR/summary.json" ]]; then
  cat "$REPORT_DIR/summary.json"
else
  echo "sanitize summary missing"
fi

echo
echo "Reports: $REPORT_DIR"
echo "Local CI complete. Review reports before committing generated artifacts."

exit "$GUARDIAN_STATUS"
