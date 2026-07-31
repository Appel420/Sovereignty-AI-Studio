# Hybrid CryptoKit/liboqs owner-approval policy

The iOS device signs the owner approval with Apple CryptoKit. The local or
self-hosted verification service validates the post-quantum signature with the
locally installed `liboqs` provider. No cloud key service is required.

```text
CryptoKit P256.Signing signature
        +
liboqs ML-DSA-87 signature
        ↓
Hybrid approval envelope
        ↓
local bridge verification
        ↓
operation may proceed only after policy checks
```

The Hybrid envelope uses:

```text
classical signature: P256.Signing (CryptoKit)
post-quantum signature: ML-DSA-87 (liboqs)
optional key establishment: ML-KEM-768 (liboqs)
payload digest: SHA-256 (CryptoKit)
state location: DEVICE_FIRST
external persistence: false by default
```

Both signatures are required. A valid CryptoKit signature alone is not enough,
and a valid liboqs signature alone is not enough. The bridge must also verify the
exact payload digest, owner key identifier, approval decision, expiration, mode,
and destination policy.

## Secure Enclave storage

`ApprovalSigner` attempts to generate a `SecureEnclave.P256.Signing.PrivateKey`
on supported Apple hardware. The private key is non-exportable in that mode.
If Secure Enclave is unavailable or key creation fails, it falls back to an
in-memory software `P256.Signing.PrivateKey` for development and unsupported
platforms.

The fallback is explicitly reported as `keychainSoftwareFallback` and must not
be presented as hardware-backed protection. A production application should
replace the in-memory fallback with a Keychain item protected by an appropriate
access-control policy before shipping.

## Verification

Swift package validation must run on a macOS/iOS host:

```bash
swift test --package-path ios
```

Local Python policy tests:

```bash
python3 -m pytest tests/test_hybrid_approval_policy.py -q
```

The Python tests inject the results of the local CryptoKit and liboqs
verification calls; they do not pretend to provide cryptographic verification
without those providers.
