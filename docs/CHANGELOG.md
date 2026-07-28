# Changelog

All notable changes to the Sovereignty AI architecture contract are recorded here.

The format follows a simplified Keep a Changelog structure. Dates use ISO 8601 format.

## [Unreleased]

### Governance

- Added repository documentation index.
- Added contribution and documentation quality rules.
- Added architecture decision record index.
- Added ADR-0001 documenting the Canonical Runtime State decision.
- Added the Local CI interface contract for self-hosted validation.
- Added local integration evidence and fail-closed preflight requirements.
- Classified Code Narration as an Experience Layer capability.
- Reserved `local-first-ci.yml` as the descriptive workflow name for the self-hosted validation contract.

## [v1.0.0-architecture] - 2026-07-28

### Added

- Normative Sovereignty AI v1.0 architecture specification.
- Root Authority and provider-neutral participant model.
- Canonical Runtime State and Mission State distinction.
- Offline, Hybrid, and Online operating-mode contracts.
- Trust-boundary and data-classification documentation.
- Stable contracts for `CanonicalStateLoader`, `AuthorityGate`, `PolicyEngine`, `Vault`, `SCARLedger`, `ParticipantRegistry`, `MarketIntelligenceCache`, `ContextEngine`, `Dashboard`, and `OwnerAlertSink`.
- Acceptance criteria for startup, authority, policy, evidence, data isolation, mission state, and dashboard availability.
- Reserved v1.1 `FeedAdapter` extension.

### Governance note

This architecture milestone is documentation-complete. It is not a claim that all executable interfaces or acceptance tests have been implemented. The `v1.0.0` release tag remains reserved for a validated implementation release.
