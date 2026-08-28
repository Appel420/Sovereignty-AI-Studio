#!/usr/bin/env bash
# Device-local CI runner.
# The device supports offline, LAN, and approved upstream/hybrid operation.
# GitHub-hosted CI is online-capable; this script does not force an offline mode.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

exec "${PYTHON:-python3}" scripts/run-local-ci.py --ci-name "${SG_CI_NAME:-ara-hardened-unit-ci-local}" "$@"
