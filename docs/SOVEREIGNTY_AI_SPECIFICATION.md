# Sovereignty AI Specification

**Operating Model:** v1.0  
**Status:** Draft for Architecture Freeze  
**Classification:** Core Platform Specification  
**Authority:** Human operator / device owner  
**Canonical state:** Required before startup  
**Default network mode:** Offline  
**Default decision:** Deny

## 1. Purpose

This specification defines the mandatory operating behavior of the Sovereignty AI platform. Authority is deterministic, private information remains under user control, network behavior is policy-driven, security-relevant actions are auditable, AI participants operate within bounded permissions, and the platform functions in disconnected, degraded, and connected environments.

## 2. Core requirements

### R-001 Human authority

The human operator remains Root Authority. No AI participant may obtain authority equal to or greater than the human operator.

### R-002 AI participants

Every participant has a unique participant ID, name, provider, version, assigned role, permission set, audit identity, configuration, and history. Participants are not human identities.

### R-003 Persistent canonical state

The platform must load and verify device-local canonical state before starting the dashboard, router, council, provider adapters, credential access, or network services. Canonical state includes authority, identity, policy, mode, audit configuration, and required storage roots.

If canonical state is missing, invalid, stale, or unverifiable, the platform must fail closed and record a local threat event. No provider access, credential access, network access, or mission execution is permitted in that condition.

### R-004 Offline operation

Offline mode must operate without network connectivity. The vault, search, memory, local inference, audit, dashboard, policy engine, and router continue functioning locally. No outbound request is permitted.

### R-005 Hybrid operation

Hybrid mode permits policy-approved retrieval of public information only. Private prompts, documents, vault contents, memories, conversations, credentials, and telemetry remain local unless an explicit scoped export is authorized.

### R-006 Online operation

Online mode remains governed by authority, policy, and audit. Network connectivity does not bypass any control.

### R-007 Explicit mode consent

Transition to a higher network mode requires explicit operator approval. Mode changes are recorded locally before the transition takes effect.

### R-008 Public market intelligence

Market intelligence is public information, such as model releases, pricing, benchmarks, advisories, provider announcements, and CVEs. It must not contain user content. Approved feeds are read-only, normalized locally, and cached.

### R-009 Local cache and degraded operation

The dashboard reads from a local cache. Feed failure must not disable the dashboard, search, history, ticker, or analytics. Cached data must show its last successful update time and freshness state.

### R-010 Evidence

Every policy-relevant event produces append-only local evidence containing timestamp, participant, action, policy decision, result, network status, and integrity hash. Placeholder signatures, fabricated health checks, and simulated audit entries are not valid evidence.

### R-011 Exact input preservation

The platform maintains separate values for `raw_input`, `policy_normalized_copy`, `confirmed_input`, and `rendered_output`. Normalization may support policy analysis but must never overwrite raw or confirmed user input. Voice transcripts require review or explicit confirmation before submission; automatic correction and automatic send are disabled by default.

### R-012 Unified workspace

The user interacts through one operational inbox. Internally, each participant retains separate history, memory, evidence, updates, configuration, and permissions. Council results are reconciled into one user-facing decision and one authorized action.

### R-013 Participant and runtime status

A registry declaration is not runtime proof. The dashboard must distinguish:

```text
DECLARED → CONFIGURED → AVAILABLE → VERIFIED → ACTIVE
```

It must also represent `UNAVAILABLE` and `DENIED`. A directory, registry entry, mock response, or generated fixture must never imply that a provider is active.

### R-014 Local-only coding execution

Local/self-hosted Linux is the authoritative execution environment. Cloud coding agents, hosted runners, and remote execution are not part of the default path. Existing routers, bridges, dashboards, model registries, council components, and local adapters must be preserved rather than replaced.

### R-015 Blocked activity evidence

Denied network access, provider access, credential access, subprocess execution, filesystem access, policy mutation, and capability escalation produce local append-only evidence.

### R-016 Council independence

Council participants have separate immutable identities, roles, permissions, configurations, histories, and evidence. Their output is advisory unless the human operator authorizes the resulting action.

## 3. Context state

The runtime must distinguish canonical runtime state from active mission state.

```text
CANONICAL STATE REQUIRED
    │
    ├── No active mission: family conversation, phone call, television,
    │   background speech, or idle
    │
    └── Owner-authenticated wake event
            │
            ▼
      ACTIVE MISSION STATE
            │
            ├── Mission
            ├── Coding
            ├── Dictation
            ├── Search
            ├── Review
            └── Administration
            │
            ▼
      Complete mission → return to no active mission
```

`No active mission` is a normal state. `No canonical state` is a threat condition and must fail closed.

## 4. Network mode matrix

| Capability | Offline | Hybrid | Online |
|---|---:|---:|---:|
| Local vault | Yes | Yes | Yes |
| Local memory | Yes | Yes | Yes |
| Dashboard | Yes | Yes | Yes |
| AI council | Yes | Yes | Yes |
| Public feed | Cached | Live + cache | Live |
| Model updates | Manual import | Policy-approved | Live, policy-approved |
| Internet search | No | Optional, policy-approved | Policy-approved |
| Telemetry upload | No | No | Policy-approved only |
| Prompt upload | No | No by default | Policy-approved only |
| Audit | Local | Local | Local, optional signed export |

## 5. Trust boundaries

```text
ROOT AUTHORITY
    ↓
Identity Plane
    ↓
AI Participants and Council Router
    ↓
Policy Boundary
    ↓
Public Intelligence Engine
    ↓
Private Data Boundary
    ↓
Experience Layer
```

Private data includes vault contents, documents, memory, sessions, keys, credentials, and evidence. Public intelligence includes model catalogs, releases, pricing, benchmarks, advisories, and CVEs. These classes must not be mixed.

## 6. Required interfaces

The architecture-freeze interfaces are:

```text
CanonicalStateLoader
IdentityProvider
AuthorityGate
PolicyEngine
ScarLedger
Vault
ContextEngine
CouncilRouter
MarketIntelligenceCache
ExperienceLayer
LocalOutbox
OwnerAlertSink
```

## 7. Non-goals for v1

Version 1 does not implement autonomous authority escalation, unrestricted internet access, provider-specific assumptions, mandatory cloud synchronization, mandatory online accounts, permanent voice recording, or automatic personal-data upload.

## 8. Acceptance criteria

### Authority

- Human authority always overrides AI.
- AI cannot modify Root Authority.
- Permission escalation is rejected and recorded.

### Offline

After disconnecting the network, the dashboard loads, the vault opens, memory and search remain accessible, local inference remains available, audit continues, and no outbound request occurs.

### Hybrid

After explicit approval, approved public feeds refresh, private vault state remains unchanged, no prompt or private-data upload occurs, the local cache updates, and the feed timestamp changes.

### Online

Policy enforcement remains active, network activity is audited, and authority remains unchanged.

### Context

Background or family conversation does not start a mission. An owner-authenticated wake event transitions into an active mission state. Completion returns to no active mission without clearing canonical runtime state.

### Evidence

A protected action produces a timestamp, participant identity, policy decision, result, network status, and verifiable integrity hash in the local append-only ledger.

## 9. Freeze condition

Version 1.0 is frozen when the Identity Plane, Authority Plane, Policy Engine, Evidence Plane, Vault, Council Router, Context Engine, Market Intelligence Engine, and Experience Layer satisfy these acceptance criteria and expose stable interfaces. Future changes should be additive and backward-compatible wherever practical.
