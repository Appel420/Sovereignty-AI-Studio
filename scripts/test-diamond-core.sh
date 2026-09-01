#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/diamond-core"

command -v cargo >/dev/null 2>&1 || { echo "FAIL: cargo is required" >&2; exit 127; }
command -v rustc >/dev/null 2>&1 || { echo "FAIL: rustc is required" >&2; exit 127; }

rustc --version
cargo --version
cargo test --all-targets
