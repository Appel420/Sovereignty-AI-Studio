# Trust Boundaries

This document supports the normative Sovereignty AI Specification v1.0.

## Boundary hierarchy

```text
Human Owner / Root Authority
  ↓
Canonical Runtime State
  ↓
Identity Plane
  ↓
Authority Gate
  ↓
Policy Engine
  ↓
Vault, SCARLedger, Participant Registry
  ↓
Mission Controller and local workspaces
  ↓
Dashboard and local cache
  ↓
Approved external adapters
```

## Rules

1. The owner is the only Root Authority.
2. AI participants and providers are non-human, bounded participants.
3. Workspace placement is not authorization.
4. Credentials are references held by the local vault or device keystore; access requires policy approval.
5. External adapters cannot bypass the Policy Engine.
6. The dashboard reads local cache and does not call providers directly.
7. Evidence remains local and append-only by default.

## Data crossing a boundary

Any private-data export requires an explicit scoped capability, owner approval, destination allowlist, purpose, duration, and `SCARLedger` evidence. Unknown destinations are denied.

## Device boundary

A user-space application can enforce its own requests and processes. Complete device-wide packet and process enforcement requires OS-level controls such as a firewall, sandbox, or network extension. The platform must report the actual enforcement layer rather than claiming coverage it does not possess.
