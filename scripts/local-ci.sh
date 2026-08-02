#!/usr/bin/env bash
# Device-local CI only: no GitHub Actions, package installation, providers, or cloud calls.
# scripts/run-local-ci.py enforces a Linux network namespace by default.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

exec "${PYTHON:-python3}" scripts/run-local-ci.py "$@"
