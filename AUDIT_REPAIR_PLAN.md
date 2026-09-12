# Production Audit / Repair Plan

Status: FAIL — current CI does not establish a production-ready build.

## Verified blockers

1. `.github/workflows/ios-sovereign-build.yml` performs source parsing and Python bytecode compilation, but explicitly records `native_xcode_compile: false`. It is therefore validation, not an iOS build.
2. The reported Python test job fails during collection because runtime dependencies are not installed: Quart, PyNaCl, FastAPI, python-jose, and Pydantic are missing.
3. `requirements.txt` declares those dependencies, but the failing workflow shown in the evidence does not install it before `pytest`.
4. `.github/workflows/Quart.yml` currently contains empty `uses:` values for both checkout and Python setup. That workflow is malformed and cannot be considered a valid CI implementation.
5. `.github/workflows/Requirements.txt` duplicates dependency ownership separately from the repository root `requirements.txt`, creating dependency drift.
6. The warning `Unknown config option: asyncio_mode` proves the pytest environment/configuration is inconsistent with the intended pytest-asyncio configuration.

## Production transport requirement

The bridge transport must be TLS-only on port 443 for WebSocket traffic (`wss://`). Plain `ws://` and HTTP bridge listeners must not be silently retained as fallbacks. Existing secure-server code already refuses startup without `TLS_CERT` and `TLS_KEY` and requires TLS 1.3, but transport configuration must be audited across the entire repository rather than assuming this single server is the only listener.

## Gate criteria

A green status is not sufficient by itself. Release readiness requires:

- dependencies installed from one authoritative lock/dependency source;
- `pip check` succeeds;
- full pytest collection succeeds;
- pytest-asyncio configuration is recognized;
- native Xcode compilation/archive is actually performed where an iOS project exists;
- all bridge listeners are inventoried and plaintext listeners are rejected or removed;
- port 443/WSS is exercised by an actual TLS handshake/integration test;
- certificate/key loading and TLS minimum version are tested;
- Merkle/evidence outputs are generated from canonical bytes and independently verified;
- deleted/renamed files are checked against imports, workflow references, package metadata, and tests;
- no job may claim a stronger validation level than it actually performs.
