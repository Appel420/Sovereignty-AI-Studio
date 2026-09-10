# Versioned seal and verification boundary

`hardware_seal.py` defines portable contracts for digest encoding, signing-key
identification, optional attestation, chain links, and independent verification.

These contracts intentionally do not claim that any hardware provider exists.
The existing TPM, SGX, and TrustZone modules return explicit unimplemented
results and must not be promoted to `HARDWARE_BACKED` or `HARDWARE_ATTESTED`
without a real provider and independent verifier.

## Strength meanings

- `software`: software key evidence only.
- `hardware_backed`: independently verified hardware-protected key evidence.
- `hardware_attested`: hardware-backed evidence plus independently verified
  attestation material.

A backend name such as `apple_secure_enclave` is metadata, not proof.
