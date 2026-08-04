#!/usr/bin/env bash
# Local-only regression entry point for the governed Hawking runtime.
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
node --check frontend/runtime/hawking-runtime.js
node --test frontend/runtime/test-hawking-runtime.test.js
