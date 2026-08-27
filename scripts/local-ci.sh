#!/usr/bin/env bash
# Deterministic local CI runner.
# Device-local mode is offline-first. GitHub-hosted CI remains online-capable.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

exec "${PYTHON:-python3}" scripts/run-local-ci.py --ci-name "${SG_CI_NAME:-ara-hardened-unit-ci-local}" "$@"
