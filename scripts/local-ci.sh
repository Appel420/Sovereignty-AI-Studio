#!/usr/bin/env bash
# Deterministic local CI runner.
# Local mode is offline-only and fails closed. Delete nothing.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Keep the canonical literal assignment visible to policy/conformance checks.
SG_NETWORK_MODE="offline"
export SG_NETWORK_MODE
export SG_LOCAL_ONLY="${SG_LOCAL_ONLY:-1}"
export SG_EXTERNAL_FEEDS="${SG_EXTERNAL_FEEDS:-disabled}"
export CLOUD_FIRST="${CLOUD_FIRST:-false}"
export PIP_NO_INDEX="${PIP_NO_INDEX:-1}"
export PIP_NO_INPUT="${PIP_NO_INPUT:-1}"
export PIP_DISABLE_PIP_VERSION_CHECK="${PIP_DISABLE_PIP_VERSION_CHECK:-1}"
export npm_config_offline="${npm_config_offline:-true}"
export npm_config_audit="${npm_config_audit:-false}"
export npm_config_fund="${npm_config_fund:-false}"
export NO_PROXY="${NO_PROXY:-*}"
export no_proxy="${no_proxy:-*}"

# Canonical local OAuth contract checks. These references are intentional CI policy invariants.
python3 scripts/validate-local-oauth.py
python3 -m pytest -q tests/test_oauth_local_generator.py

exec "${PYTHON:-python3}" scripts/run-local-ci.py --ci-name "${SG_CI_NAME:-ara-hardened-unit-ci-local}" "$@"
