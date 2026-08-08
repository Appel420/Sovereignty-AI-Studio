#!/usr/bin/env bash
# Deterministic local CI. No GitHub Actions, cloud agents, publishing, or provider calls.
# Owner policy: self-hosted Linux arm64. Fail closed. Delete nothing.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

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

# Enforce local shell-only gate behavior before handing off to Python runner.
exec "${PYTHON:-python3}" scripts/run-local-ci.py "$@"
