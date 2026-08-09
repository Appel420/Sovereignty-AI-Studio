#!/usr/bin/env bash
# Deterministic local CI runner.
# Supports local-first execution; hybrid/online authorization is handled by
# scripts/run-local-ci.py via the CI name and explicit confirmation flag.
# Owner policy: self-hosted Linux arm64. Fail closed. Delete nothing.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Local-first defaults.
export SG_NETWORK_MODE="${SG_NETWORK_MODE:-offline}"
export SG_LOCAL_ONLY="${SG_LOCAL_ONLY:-1}"
export SG_EXTERNAL_FEEDS="${SG_EXTERNAL_FEEDS:-disabled}"
export CLOUD_FIRST="${CLOUD_FIRST:-false}"

# Package-manager safety defaults for offline/local validation.
export PIP_NO_INDEX="${PIP_NO_INDEX:-1}"
export PIP_NO_INPUT="${PIP_NO_INPUT:-1}"
export PIP_DISABLE_PIP_VERSION_CHECK="${PIP_DISABLE_PIP_VERSION_CHECK:-1}"
export npm_config_offline="${npm_config_offline:-true}"
export npm_config_audit="${npm_config_audit:-false}"
export npm_config_fund="${npm_config_fund:-false}"
export NO_PROXY="${NO_PROXY:-*}"
export no_proxy="${no_proxy:-*}"

# Hand off to the repository's local validation runner.
exec "${PYTHON:-python3}" scripts/run-local-ci.py "$@"
