#!/usr/bin/env bash
# Deterministic local CI runner.
# Local mode is offline-first. Delete nothing.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Canonical local mode contract. These literals are intentional governance invariants.
SG_NETWORK_MODE="offline"
export SG_NETWORK_MODE
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

# Canonical local OAuth contract checks. These references are intentional CI policy invariants.
python3 scripts/validate-local-oauth.py
python3 -m pytest -q tests/test_oauth_local_generator.py

exec "${PYTHON:-python3}" scripts/run-local-ci.py --ci-name "${SG_CI_NAME:-ara-hardened-unit-ci-local}" "$@"
