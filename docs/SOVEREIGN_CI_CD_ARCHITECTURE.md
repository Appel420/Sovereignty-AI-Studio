# Sovereign CI/CD Architecture Note
## L6 / GateOne Integration for Environmental Vector Hardening

**Date:** 2026-06-16  
**Context:** xAI / Grok / Starshield / Tesla-class workloads (IL6-class requirements)  
**Focus:** Environmental vector from the 4-vector causal model (Internal / External / Human / Environmental). This layer secures the build & supply chain surface.

### 1. Purpose
These workflows close the loop on the **Environmental vector** by enforcing:
- Post-quantum cryptographic attestation (ML-DSA-87 primary + ML-DSA-65 fallback) on every build and artifact.
- Hardware-rooted identity where possible (via `crypto_backends.py` patterns: TPM 2.0, Secure Enclave, Android Keystore).
- Immutable audit emission (SCAR-style + LiveTerminal ports 9897/9898/9899 hooks).
- Supply-chain security (cosign keyless + SBOM + in-toto style attestation).
- Clean separation: high-assurance L6 paths vs. lower-tier traffic.

This directly supports the GateOne PQC verifier + token generator we built and the `meta-fortress.sh` / DNS hardening patterns.

### 2. The Two Workflows

| Workflow                        | Trigger                  | Primary Scope                     | Key L6 Features                                      | Integration Points |
|--------------------------------|--------------------------|-----------------------------------|------------------------------------------------------|--------------------|
| `oauth-api-generator.yml`      | Tags, Releases, Manual   | Python/FastAPI/Docker sovereign stack | ML-DSA-87+65, real GateOne `/verify-attestation` call, key rotation, SCAR emission | GateOne verifier, sovereign.pqc_signatures, LiveTerminal |
| `ios-sovereign-build.yml`      | Push/PR to main          | iOS / Secure Enclave / StreamStudioApp | XcodeGen + PQC-backed build attestation, Secure Enclave helper hooks, ML-DSA manifest signing | crypto_backends (darwin path), GateOne token, sovereign security module |

### 3. How They Map to the Broader Stack
- **GateOne PQC Verifier** (`gateone_pqc_verifier.py`): Both workflows call or emulate the `/verify-attestation` and token generation logic (ML-DSA-87 primary with automatic 65 fallback + TPM quote check).
- **crypto_backends.py**: iOS workflow uses the `darwin` / `ios` signer path (Secure Enclave Ed25519 + X25519). Python workflow can call the TPM / software fallback path.
- **LiveTerminal + SCAR**: Optional step in both to POST a minimal signed event to the sovereign orchestrator (ports 9897/9898/9899) when `SOVEREIGN_LIVETERMINAL_URL` is set.
- **Q-Resist / kill-chain**: Future extension — on failed attestation the workflow can emit a block signal.
- **4-Vector Model**: These workflows primarily harden the **Environmental** vector (build platform, dependency graph, CI runner compromise surface) while feeding evidence back into discovery/audit for the other vectors.

### 4. Gating & Promotion Strategy
- `build-test` → `sovereign-security` (mandatory, blocks promotion)
- `sovereign-security` must produce a valid ML-DSA-87 attestation token
- Docker path is **release-gated** only (tags + published releases)
- iOS path runs on every main/PR for fast feedback, but full PQC + Enclave signing is enforced on tags/releases
- Failed attestation → workflow fails + optional SCAR alert

### 5. Next Evolution Steps
1. Move `sovereign.pqc_signatures` and `gateone_pqc` into a proper installable package (`sovereign-core`).
2. Add real Secure Enclave code-signing step in the iOS workflow (custom Xcode script phase + `crypto_backends` bridge).
3. Wire both workflows to emit structured SCAR logs to the persistent brain / Enclave.
4. Add `ara-hardened` branch protection + required status checks from these two workflows.

This pair of workflows, together with the GateOne verifier, `crypto_backends.py`, and the meta-fortress hardening, forms the current **Environmental control plane** for the sovereign stack.

---

**Status:** Production-ready skeleton. Ready for `ara-hardened` integration and live testing against a running GateOne instance.