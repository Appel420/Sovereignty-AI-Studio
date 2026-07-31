# Sovereignty AI Documentation Index

This directory contains the normative architecture specification and the supporting governance documents for Sovereignty AI v1.0.

## Normative authority

- [Sovereignty AI Specification v1.0](SOVEREIGNTY_AI_SPECIFICATION_v1.0.md) — the authoritative operating model and stable contracts.

## Architecture references

- [Trust boundaries](architecture/trust-boundaries.md)
- [Runtime lifecycle](architecture/runtime-lifecycle.md)
- [Data classification](architecture/data-classification.md)

## Interface contracts

- [CanonicalStateLoader](interfaces/canonical-state-loader.md)
- [AuthorityGate](interfaces/authority-gate.md)
- [PolicyEngine](interfaces/policy-engine.md)
- [SCARLedger](interfaces/scar-ledger.md)
- [ParticipantRegistry](interfaces/participant-registry.md)
- [MarketIntelligenceCache](interfaces/market-intelligence-cache.md)

## Architecture decisions

- [ADR index](adr/README.md)
- [ADR-0001: Canonical Runtime State](adr/ADR-0001-canonical-runtime-state.md)

## Governance principles

1. The human device owner is the only Root Authority.
2. Canonical Runtime State is required before platform operation.
3. Mission State is transient and never grants authority.
4. The default network mode is Offline.
5. The default policy decision is `DENY`.
6. Policy-relevant actions produce local append-only `SCARLedger` evidence.
7. Documentation changes that alter normative behavior require change control.

Supporting documents explain or organize the specification; they do not override it. If documents conflict, the normative specification and approved architecture decisions take precedence.
