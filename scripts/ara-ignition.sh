#!/usr/bin/env bash
# ara-ignition.sh
# GitHub-hosted valet: cheap, low-bearing, runs only when needed.
# Starts the car. Does not drive the device.
set -Eeuo pipefail

RUN_ID="${GITHUB_RUN_ID:-local}"
SHA="${GITHUB_SHA:-unknown}"
REF="${GITHUB_REF:-unknown}"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > ara-handoff.json <<EOF
{
  "who": "ara-ignition",
  "what": "github-hosted-ignition-pass",
  "when": "${TS}",
  "where": "ubuntu-latest",
  "why": "valet-start-car-before-sovereign-shift",
  "how": "bash scripts/ara-ignition.sh",
  "run_id": "${RUN_ID}",
  "sha": "${SHA}",
  "ref": "${REF}",
  "status": "ready-for-handoff"
}
EOF

echo "ARA_IGNITION=PASS run_id=${RUN_ID} sha=${SHA}"
