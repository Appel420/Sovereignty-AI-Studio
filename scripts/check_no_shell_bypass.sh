#!/usr/bin/env bash
# Regression gate for issues #898 / #899.
# Fails the build if ALLOW_SHELL=1 or silent 2>/dev/null shell-bypass patterns reappear
# in the live execution surface (not external/ docs).
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail=0

# 1) No ALLOW_SHELL=1 enablement in package scripts or server entrypoints
if grep -RIn --exclude-dir=external --exclude-dir=node_modules --exclude-dir=.git \
  -E 'ALLOW_SHELL[[:space:]]*=[[:space:]]*1' package.json server_9899.js node-bridge 2>/dev/null; then
  echo "FAIL: ALLOW_SHELL=1 enablement found (issue #898/#899)"
  fail=1
fi

# 2) No exec of arbitrary shell gated by ALLOW_SHELL in server_9899.js
if grep -n "ALLOW_SHELL" server_9899.js 2>/dev/null | grep -v 'REMOVED\|fail-closed\|echo-only'; then
  echo "FAIL: residual ALLOW_SHELL reference in server_9899.js"
  fail=1
fi

# 3) package.json must not expose a shell script that enables the bypass
if grep -E '"shell"[[:space:]]*:' package.json 2>/dev/null; then
  echo "FAIL: package.json still defines a shell script entry"
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  echo "SCAR_STATUS=FAIL"
  echo "SCAR_REASON=shell-bypass-regression"
  exit 1
fi

echo "SCAR_STATUS=PASS"
echo "SCAR_JOB=check_no_shell_bypass"
echo "OK: no ALLOW_SHELL bypass surface in live paths"
