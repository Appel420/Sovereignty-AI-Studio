# Sovereignty AI Specification v1.0

**Status:** Normative Architecture Specification  
**Authority:** Human Owner  
**Default Mode:** Offline  
**Default Decision:** Deny  
**Classification:** Core Platform Specification  
**Canonical API spelling:** `SCARLedger`

## Part I — Normative Requirements

### 1. Authority Model

1. The device owner is the only Root Authority.
2. AI participants are advisory by default.
3. Authority cannot be delegated implicitly.
4. No AI participant, provider, service, or repository may grant itself authority, modify Root Authority, or change policy without explicit owner authorization.
5. Credential possession does not imply permission.
6. Sensitive actions require a scoped capability with an owner decision, an intended purpose, scope, expiry, and audit identity.

### 2. Identity Model

Every participant SHALL have a unique immutable Participant ID that survives software upgrades and does not depend on a provider API. Each participant record SHALL contain:

- Participant ID
- display name
- category (`Human`, `AI`, `Service`, or `System`)
- provider and model, when applicable
- role
- capabilities
- permissions
- workspace
- memory allocation
- evidence stream
- version
- trust status
- configuration history

AI participants SHALL NOT be treated as human identities.

### 3. Canonical Runtime State

Canonical Runtime State is always required. It remains loaded during idle and active missions and includes:

- Root Authority
- identity database
- policy engine configuration
- `SCARLedger`
- encrypted vault metadata
- trust anchors
- configuration
- local cache metadata
- cryptographic key references
- AI participant registry
- workspace index

Missing, invalid, stale, or unverifiable canonical state is a threat condition. The platform SHALL fail closed, record local evidence, alert the owner when possible, and deny provider, credential, mission, and external-network capabilities.

### 4. Mission State

Mission State is transient and changes behavior only. Valid states include `NO ACTIVE MISSION` and `ACTIVE MISSION`. Examples of active work include coding, research, conversation, planning, dictation, search, review, and administration. Family conversation, phone calls, television, background speech, and idle activity are not missions unless an owner-authenticated wake event activates one.

Canonical Runtime State never disappears during a mission transition.

### 5. Network Modes

#### Offline

The platform SHALL operate without network connectivity. Vault, local memory, local inference, search, dashboard, policy, router, and audit remain available. Provider APIs and external retrieval are denied.

#### Hybrid

Hybrid permits policy-approved public-information retrieval only. It remains deny-by-default and is not a trust mode. Private prompts, documents, vault contents, memories, conversations, credentials, and telemetry SHALL remain local unless a separate explicit owner-approved export capability exists.

#### Online

Online permits policy-approved connectivity only. Network access SHALL NOT bypass authority, policy, audit, data classification, or owner approval.

Transition to a higher network mode requires explicit owner approval.

### 6. Data Boundaries

- **Authority:** Root ownership and permissions; local; never exported without explicit approval.
- **Private:** Vault, memory, conversations, documents, credentials, and sessions; local; never leaves by default.
- **Public:** Model catalogs, releases, pricing, benchmarks, advisories, and availability; local cache; refreshable under policy.
- **Evidence:** Audit events, hashes, and signatures; local append-only ledger; optional signed export only.

The dashboard SHALL read from local cache and SHALL NOT communicate directly with external providers.

### 7. Evidence Requirements

Every policy-relevant action SHALL produce an append-only `SCARLedger` event containing timestamp, participant, action, policy version, result, reason, request identity, and integrity hash. Evidence SHALL be written locally before recovery or follow-up action. Credentials, session keys, raw private payloads, and secrets SHALL never be recorded.

### 8. Context and Workspace

The platform SHALL provide one operational inbox while retaining participant-specific history, memory, evidence, updates, configuration, notes, and cached artifacts in separate workspaces. Workspace membership does not grant provider permission.

## Part II — Stable Interface Contracts

Every interface has a stable purpose, inputs, outputs, failure behavior, and audit requirements. Core interfaces are:

`CanonicalStateLoader`, `IdentityProvider`, `AuthorityGate`, `PolicyEngine`, `Vault`, `SCARLedger`, `ParticipantRegistry`, `MarketIntelligenceCache`, `ContextEngine`, `Dashboard`, and `OwnerAlertSink`.

### Policy Decision Values

Implementations SHALL use exactly:

- `ALLOW`
- `DENY`
- `REQUIRE_APPROVAL`

### Startup Contract

No provider adapter, polling loop, WebSocket, Server-Sent Events stream, credential consumer, or external network client may initialize before `PolicyEngine` succeeds.

## Part III — Runtime

### Startup Sequence

```text
Power On
  ↓
Hardware Validation
  ↓
Canonical State Loader
  ↓
Integrity Verification
  ├── FAIL → local threat evidence → owner alert → fail closed
  └── PASS
       ↓
Identity Provider
       ↓
Authority Gate
       ↓
Policy Engine
       ↓
Vault
       ↓
SCARLedger
       ↓
Participant Registry
       ↓
Market Intelligence Cache
       ↓
Dashboard
       ↓
Await Mission
```

### Failure Handling

Failures SHALL be deterministic. The platform SHALL deny the affected capability, append evidence, preserve cached local functionality where safe, alert the owner, and avoid automatic escalation. If the policy engine is unavailable, all network capabilities are disabled.

### Market Intelligence

Approved public sources are normalized, validated, timestamped, optionally signed, and written to the local cache before dashboard use. `FeedAdapter` is a v1.1 extension; v1.0 owns only `MarketIntelligenceCache`.

## Part IV — Acceptance Criteria

### Startup

- Missing canonical state denies startup.
- Invalid, stale, or unverifiable state denies startup and produces local evidence.
- Valid state permits identity, authority, and policy initialization.
- No external client initializes before policy success.

### Security and Data Isolation

- Human authority always overrides AI.
- AI authority-change requests are denied and recorded.
- Secrets and raw private payloads never enter evidence.
- Offline mode denies external network and provider APIs.
- Hybrid mode denies private-data upload by default.
- Online mode remains policy- and audit-controlled.

### Mission and Dashboard

- Inactive missions cannot execute mission actions.
- Active missions remain policy-bound.
- Empty or stale cache does not block dashboard navigation, search, filters, or workspaces.
- Provider unavailability leaves cached data visible.

## Mode Matrix

| Capability | Offline | Hybrid | Online |
|---|---:|---:|---:|
| Canonical State | ✓ | ✓ | ✓ |
| Vault | ✓ | ✓ | ✓ |
| SCARLedger | ✓ | ✓ | ✓ |
| Dashboard | ✓ | ✓ | ✓ |
| Local Models | ✓ | ✓ | ✓ |
| Public Feed | Cached | Cached + Refresh | Live + Cache |
| Provider APIs | ✗ | Policy-approved | Policy-approved |
| Personal Data Upload | ✗ | ✗ by default | Policy-controlled |
| Audit | Local | Local | Local + optional signed export |

## Appendix A — Trust Boundaries

```text
HUMAN OWNER / ROOT AUTHORITY
        ↓
CANONICAL RUNTIME STATE
        ↓
IDENTITY → AUTHORITY → POLICY → VAULT / SCAR / REGISTRY
        ↓
MISSION CONTROLLER
        ↓
LOCAL WORKSPACES AND DASHBOARD CACHE
        ↓
APPROVED PROVIDER OR PUBLIC-FEED ADAPTER
```

## Appendix B — Informative FeedAdapter Example

`FeedAdapter` is not a v1.0 core interface. A future adapter may expose `connect()`, `fetch()`, `normalize()`, `validate()`, `cache()`, and `status()`, feeding only `MarketIntelligenceCache`.

## Appendix C — Informative Provider Examples

Providers such as OpenAI, Anthropic, xAI, GitHub Models, Hugging Face, or other services are examples only. Provider names do not change the normative authority, policy, identity, audit, or data-boundary requirements.

## Versioning

Version 1.0 is frozen when the core interfaces and acceptance criteria are implemented and tested. Future changes should be additive and backward-compatible wherever practical.
