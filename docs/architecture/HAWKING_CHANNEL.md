# Hawking Channel Runtime Contract

`SovereignHawkingChannel` is the encrypted message boundary for SGHv119. It is a transport-neutral module, not an automatic network client.

## Current browser algorithms

The browser implementation uses:

- P-256 ECDH for session key agreement.
- HKDF-SHA-256 for session-key derivation.
- AES-256-GCM for authenticated encryption.
- ECDSA P-256/SHA-256 for sender signatures.

It does not claim X25519 or Ed25519 support. Those algorithms require a verified native or WebCrypto adapter and must not be represented as active merely because a dashboard label says so.

## Modes

- `local` and `offline`: seal the message and dispatch `sg:hawkingMsg` locally. No relay, satellite, mesh, or external fetch is attempted.
- `hybrid` and `online`: require an explicit caller-supplied transport function. This module does not read relay URLs from storage and does not invent endpoints.

## Identity and key handling

Keys are generated in memory for the session. Private keys are not written to `localStorage`. Device-persistent identity requires an approved local keystore adapter and explicit owner policy.

## Integration rule

The dashboard must show the channel as `DECLARED`, `AVAILABLE`, `VERIFIED`, or `ACTIVE` only after the corresponding runtime check. `READY` means the browser session channel initialized; it does not mean a remote peer, satellite, mesh relay, certificate, mTLS path, or PQC signer is active.

## SGHv119 wiring

The module is intentionally added before wiring the monolithic dashboard. The next integration step must replace duplicate Hawking code with this single module and connect its status to the existing dashboard indicator without adding another retry loop or outbound path.
