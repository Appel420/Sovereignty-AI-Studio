#!/usr/bin/env bash
# Device-local CI runner.
# The PHONE/DEVICE is the sovereign execution boundary. GitHub is not this runner.
# Dependencies are consumed from the device's existing environment; this script
# never installs packages and never requires an external network.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export SG_NETWORK_MODE=local
export SG_LOCAL_ONLY=1
export SG_EXTERNAL_FEEDS=disabled
export CLOUD_FIRST=false
export PIP_NO_INDEX=1
export PIP_NO_INPUT=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export npm_config_offline=true
export npm_config_audit=false
export npm_config_fund=false
export NO_PROXY="*"
export no_proxy="*"

# Keep the canonical OAuth contract explicitly visible to local CI. This is a
# validation reference only; the validator itself remains network-free.
"${PYTHON:-python3}" scripts/validate-local-oauth.py

# Keep the OAuth generator contract independently visible as a local test.
"${PYTHON:-python3}" -m pytest -q tests/test_oauth_local_generator.py

exec "${PYTHON:-python3}" scripts/run-local-ci.py --ci-name "${SG_CI_NAME:-ara-hardened-unit-ci-local}" "$@"
