#!/usr/bin/env bash
# Deterministic device-local CI runner.
# The device supports offline operation; GitHub-hosted CI remains online-capable.
set -Eeuo pipefail

# Explicit local/offline contract for the device runner.
export SG_NETWORK_MODE=local
export PIP_NO_INDEX=1

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

exec "${PYTHON:-python3}" scripts/run-local-ci.py --ci-name "${SG_CI_NAME:-ara-hardened-unit-ci-local}" "$@"
