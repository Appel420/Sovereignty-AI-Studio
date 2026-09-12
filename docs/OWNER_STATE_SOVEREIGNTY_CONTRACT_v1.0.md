# Owner State Sovereignty Contract v1.0

**Status:** LOCKED
**Authority:** Human device owner
**Scope:** device state, authentication, continuity, execution, external routing, council verification, retention, and evidence

## Governing hierarchy

```text
HUMAN DEVICE OWNER
        |
        v
ROOT AUTHORITY / OWNER SESSION
        |
        v
OWNER DEVICE
  |-- identity + keys
  |-- canonical state
  |-- persistent memory
  |-- reasoning / task continuity
  |-- policies + approvals
  `-- SCAR evidence
        |
        v
ACTIVE SESSION (stateful)
        |
        v
AUTHORIZED WORK
   |-- LOCAL
   `-- EXTERNAL (stateless by default)
        |
        v
RESULT + EVIDENCE
        |
        v
DEVICE STATE UPDATED
```

## Non-negotiable invariants

1. **Owner is never an outsider on the owner's device.** Authentication restores access to the owner's verified state. It does not require external permission to use owner-controlled data.
2. **Stateful on device, stateless when leaving.** External models, agents, providers, and execution nodes receive only minimum authorized working context. They do not become owners of memory, identity, keys, authority, or continuity.
3. **Work is never held hostage.** External route, provider, model, or service unavailability must not block authorized local work. Local execution, queued state, and approved alternate routes remain available where capable.
4. **Reasoning continuity is durable and owner-controlled.** Preserve inspectable evidence and concise rationale; do not require or expose private model chain-of-thought.
5. **Council operates inside the owner state boundary.** Council output is advisory and cannot silently substitute for owner authority.
6. **Transparency is mandatory.** Authorization, access denial, state used, network status, retention status, and local evidence must be owner-visible.
7. **Execution, state, and retention are independent authorization domains.** Remote execution does not grant memory authority, and network access does not grant storage consent.
8. **Every authorized state transition is evidence-bearing.**

## Authentication and continuity

```text
OWNER AUTHENTICATION
        |
        v
CANONICAL STATE VERIFY
        |
        v
IDENTITY + FEATURE RESOLUTION
        |
        v
EFFECTIVE POLICY
        |
        v
STATEFUL ACTIVE SESSION
```

Authentication is an owner-session restoration mechanism. It is not memory consent, external synchronization consent, or provider authorization.

## Execution boundary

```text
DEVICE STATE
    |
    +--> LOCAL EXECUTION
    |
    `--> APPROVED EXTERNAL EXECUTION
              |
              +--> minimum context
              +--> scoped capability
              +--> explicit policy
              +--> evidence
              `--> no default retention
```

External execution returns a result and evidence to the device. Canonical continuity remains device-local.

## Reasoning evidence contract

```text
request
  -> state snapshot/version
  -> policy decision
  -> capability
  -> model/council observations
  -> concise rationale
  -> result
  -> verification
  -> SCAR evidence
  -> device state transition
```

The system preserves decision-relevant evidence rather than exposing private hidden reasoning.

## Council / hallucination protection

The council may evaluate contradictions, unsupported claims, missing provenance, state mismatch, and verification disagreement.

On material disagreement:

```text
🚨 OWNER ALERT
STATUS: REVIEW REQUIRED
AUTHORIZATION: NOT GRANTED / ACTION PAUSED
REASON: verification disagreement / state contradiction / provenance failure
DATA EXPORTED: NONE unless already explicitly authorized
```

A confidence or risk signal never grants authority.

## Owner-visible display contract

Normal state:

```text
OWNER: AUTHENTICATED
DEVICE STATE: AVAILABLE
LOCAL WORK: AVAILABLE
MEMORY: OWNER-CONTROLLED
EXTERNAL ROUTES: OPTIONAL
PROVIDER ACCESS: SCOPED
```

Blocked action:

```text
OWNER ACCESS: ALLOWED
REQUESTED ACTION: BLOCKED
REASON: scope / confirmation / capability
RECOVERY: available to owner
DATA SENT: none
```

The distinction is mandatory:

```text
OWNER ACCESS != ACTION AUTHORIZATION
ONLINE != PERMISSION
EXECUTION != OWNERSHIP
ASSISTANT != AUTHORITY
```

## State classes

### DEVICE_LOCAL

Default and authoritative. Includes conversations, checkpoints, task state, approvals, owner preferences, repository/workspace context, audit, and SCAR evidence.

### EXTERNAL_EPHEMERAL

Permitted only for an explicitly approved execution. Minimum authorized context is sent for execution and discarded after return unless retention is separately authorized.

### EXTERNAL_PERSISTENT

Blocked by default. Requires explicit owner authorization, named destination, visible fields, declared retention, revocation path, audit, and result verification.

## Work-continuity invariant

```text
EXTERNAL FAILURE
      |
      +--> LOCAL CAPABILITY AVAILABLE -> CONTINUE
      |
      +--> APPROVED ALTERNATE ROUTE -> CONTINUE
      |
      `--> NO CAPABLE ROUTE
              |
              v
        PRESERVE TASK STATE
              |
              v
        INFORM OWNER / RESUME LATER
```

No external provider may become a single point of authority for the owner's authorized work.

## Evidence

Every completed operation produces a state report containing, at minimum:

```json
{
  "state_used": "DEVICE_LOCAL",
  "external_data_sent": false,
  "external_state_written": false,
  "policy_verified": true
}
```

Blocked external synchronization must record that no data was transmitted. Authorized external state movement must identify destination, fields transferred/excluded, retention, authorization, and result.

## Governance boundary

Development lanes, integration branches, execution adapters, providers, and councils are subordinate to owner authority. They may coordinate and execute within granted scope but may not silently acquire ownership of state, identity, keys, memory, or continuity.

Promotion remains owner-controlled and evidence-bearing. No component may treat access as authority or provider claims as a trust anchor.
