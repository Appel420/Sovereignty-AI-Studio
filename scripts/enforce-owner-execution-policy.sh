#!/usr/bin/env bash
# Owner-approved local gate. Never installs, deletes, publishes, or contacts cloud services.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export SG_NETWORK_MODE=offline
export SG_LOCAL_ONLY=1
export SG_EXTERNAL_FEEDS=disabled
export PIP_NO_INDEX=1
export PIP_NO_INPUT=1
export npm_config_offline=true

python3 scripts/enforce-owner-execution-policy.py
