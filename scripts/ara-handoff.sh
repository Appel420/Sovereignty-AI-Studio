#!/usr/bin/env bash
# ara-handoff.sh
# Self-hosted ARM64 shift: device picks up the workload.
# No constant pounding. Gated by ignition success.
set -Eeuo pipefail

if [[ ! -f ara-handoff.json ]]; then
  echo "No handoff artifact found. Refusing to run blind."
  exit 1
fi

echo "Picking up handoff:"
cat ara-handoff.json

# Device-side work goes here. Keep it bounded.
# Example: run local CI, validate runtime coherence, etc.
if [[ -x ./scripts/local-ci.sh ]]; then
  ./scripts/local-ci.sh
else
  echo "local-ci.sh not present; skipping device CI."
fi

echo "ARA_HANDOFF=COMPLETE"
