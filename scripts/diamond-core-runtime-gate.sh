#!/usr/bin/env bash
# Diamond Lattice 5D Core runtime gate.
# Fail closed: the canonical local runtime must not start when the contract
# crate is absent, the workspace is invalid, or any contract test fails.
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CARGO_BIN="${CARGO_BIN:-cargo}"
CORE_MANIFEST="$ROOT_DIR/diamond-core/Cargo.toml"

[[ -f "$CORE_MANIFEST" ]] || { echo "DIAMOND_CORE=DENY missing Cargo.toml" >&2; exit 1; }
command -v "$CARGO_BIN" >/dev/null 2>&1 || { echo "DIAMOND_CORE=DENY cargo unavailable" >&2; exit 1; }

# Contract verification is deliberately pure software. No network access,
# accelerator initialization, package installation, or provider calls occur.
CARGO_NET_OFFLINE=true "$CARGO_BIN" test --manifest-path "$CORE_MANIFEST" --all-targets --locked

echo "DIAMOND_CORE=PASS"
echo "DIAMOND_CORE_MANIFEST=$CORE_MANIFEST"
