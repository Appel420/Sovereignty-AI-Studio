# Device State Sovereignty Policy v1.1.1

**Status:** LOCKED  
**Branch:** ara-hardened  
**Owner authority:** Human owner only  

## Core invariants

```
DEVICE STATE IS DEFAULT
EXTERNAL STATE IS OPT-IN
HIDDEN STATE IS FORBIDDEN
UNAUTHORIZED SYNC IS BLOCKED
LOGIN ≠ MEMORY CONSENT
NETWORK ≠ STORAGE CONSENT
EXECUTION ≠ OWNERSHIP
ASSISTANT ≠ AUTHORITY
```

## Separation of controls

| Control | Meaning |
|---------|---------|
| EXECUTION PERMISSION | May a model run / answer |
| STATE PERSISTENCE PERMISSION | May state be written |
| DATA RETENTION PERMISSION | May data be kept beyond the request |

These three are independent. Remote execution does **not** grant memory authority.

## Canonical state policy object

Every request that can touch state must resolve this before routing:

```json
{
  "state_policy": {
    "mode": "DEVICE_ONLY",
    "allow_external_memory": false,
    "allow_provider_training": false,
    "allow_cross_session_sync": false,
    "allow_telemetry": false
  }
}
```

### Modes

**Ghost / DEVICE_ONLY**
- State location: device only
- External persistence: prohibited
- External synchronization: prohibited
- Network: false (or loopback only)

**Hybrid / DEVICE_FIRST**
- State location: device first
- External state: per-operation opt-in
- Every transfer explicit, fields logged, destination named
- No silent synchronization

**Online**
- External state still OPT_IN_ONLY
- Provider identity, fields, retention, and revocation must be visible

## State classes

- **DEVICE_LOCAL** — default authority. Conversations, session checkpoints, agent state, approvals, task history, local audit, owner preferences.
- **EXTERNAL_EPHEMERAL** — allowed only for the duration of an approved execution. Context discarded after response. No memory, no profile, no retention.
- **EXTERNAL_PERSISTENT** — blocked by default. Requires explicit owner authorization, named destination, visible fields, retention policy, revocation path, and an audit event.

## Hybrid continuity (device-local only)

Hybrid is **not** provider memory. It is the device-local cross-agent continuity record:

```
state/
├── agents/          # per-agent detailed files
├── hybrid/          # aggregate continuity (day / week / month / year)
└── audit/           # append-only evidence
```

Every hybrid record carries WHO / WHAT / WHERE / WHEN / WHY / HOW + PROOF.

## Bridge validation rule

Before any external route:

1. Resolve `state_policy`
2. Ask: can the destination satisfy the policy?
3. YES → proceed with evidence
4. NO → block with reason `STATE_SYNC_BLOCKED` and transmit nothing

## Evidence requirement

Every completed operation produces a state report:

```json
{
  "state_used": "DEVICE_LOCAL",
  "external_data_sent": false,
  "external_state_written": false,
  "policy_verified": true
}
```

Authorized external sync additionally records `authorization_id`, destination, fields transferred, fields excluded, and retention.

## Human-owner collaboration gate

Privileged or mutating actions (policy change, key use, vault unlock, capability escalation, external sync, branch merge to main) require active collaboration / approval from the human owner entity. Council or model output remains advisory until that gate is passed.

## Display requirements

The terminal / dashboard must continuously show:

```
STATE LOCATION: DEVICE LOCAL
EXTERNAL MEMORY: DISABLED
SYNC: DISABLED / NOT CONFIGURED
TRAINING USE: NOT AUTHORIZED
```

When external persistence is authorized, the same surface must show destination, fields, retention, and owner controls (EXPORT | REVOKE | DELETE).

## Non-negotiable

- No silent state transfer
- No provider-owned conversation continuity by default
- No fabricated evidence scores or risk numbers
- No push to `main` without explicit owner consent
- All work on dedicated agent branches (this policy lives on `ara-hardened`)
