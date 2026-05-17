# Technical Whitepaper — Sovereignty-One v2.3

## 1. Architecture Overview

Sovereignty-One is a layered sovereign AI stack designed for maximum privacy, tamper-evidence, and hardware-rooted trust.

Layers:
- Encryption Core (QuadRatchet + Merkle)
- RAG Layer (encrypted vector stores)
- Daemon Layer (async service with observability)
- Security Perimeter (Citadel + TPM + SGX)

## 2. TPM 2.0 Attestation

Full remote attestation using tpm2-pytss:
- PCR quote generation
- ESAPI for quote creation and verification
- Nonce freshness + signature validation
- Integration with QuadRatchet for sealed secrets

Code in core/security/tpm_attestation.py

## 3. Intel SGX Secure Enclaves

Added SGX integration for runtime memory encryption and attestation:
- Enclave creation with Intel SGX SDK simulation + production path
- Remote attestation (EPID + DCAP)
- Sealed storage for keys (similar to TPM but for application memory)
- Integration point: core/security/sgx_enclave.py
- Use case: Protect sensitive EEG data and model weights in-enclave

## 4. Full Module List

(See individual files for implementation)

## 5. Security Model

- Forward secrecy + break-in recovery
- Merkle-chained immutable audit (SCAR)
- Circuit breaker for resilience
- No cloud leakage by design

**Version:** 2.3 | Date: 2026-05-17