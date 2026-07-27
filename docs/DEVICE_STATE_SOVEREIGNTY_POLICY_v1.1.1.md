# Device State Sovereignty Policy v1.1.1

**Status:** Authoritative behavioral and state-governance contract  
**Scope:** SGHv119 dashboard, local device bridge, Hybrid continuity, agent sessions, external inference, synchronization, audit, SCAR evidence, visible connection state, and repository promotion.

## Governing rule

> THE DEVICE OWNS STATE.  
> THE USER OWNS AUTHORIZATION.  
> THE PROVIDER ONLY RECEIVES APPROVED CONTEXT.

The device-local state store is the source of truth for continuity. External providers may execute approved requests, but they do not become the source of truth for conversations, identity, approvals, task history, or session continuity.

## Enforcement model

```text
OWNER
  |
  v
DEVICE AI / BRIDGE
  |
  +-----------------------+
  |                       |
  v                       v
LOCAL STATE STORE     EXTERNAL PROVIDER
AUTHORITY             EXECUTION ONLY
  |                       |
  v                       v
CONVERSATIONS,       APPROVED CONTEXT
CHECKPOINTS,         ONLY; NO HIDDEN
AUDIT, APPROVALS     RETENTION
```

## State classes

### DEVICE_LOCAL

The default and authoritative state class. It includes conversations, per-agent session files, Hybrid continuity records, session checkpoints, agent state, approvals, task history, local repository and workspace context, local audit and SCAR evidence, and owner preferences.

**Control:** owner-controlled and device-local.

### EXTERNAL_EPHEMERAL

Allowed only for an explicitly approved execution:

```text
User request
  -> approved context slice
  -> remote inference or external execution
  -> response returned
  -> context discarded
```

Required properties:

```text
memory: none
profile: none
sync: none
retention: none
```

### EXTERNAL_PERSISTENT

Blocked by default. It requires explicit owner authorization, a named destination, visible fields, a declared retention policy, a revocation path, an audit and SCAR event, and successful result verification.

## Hybrid continuity

Hybrid is a device-local aggregate continuity layer. It combines verified records from each agent without moving authority to an external provider.

```text
Per-agent DEVICE_LOCAL records
  -> device-local Hybrid continuity file
  -> SGHv119 dashboard resume state
```

The Hybrid record preserves the who, what, when, where, why, and how of verified work across the day, week, month, and year. Per-agent detailed records remain authoritative for individual conversations. The Hybrid file is the device-local aggregate used to resume work across agents and sessions. External providers never become the continuity source.

Each aggregate record must identify its state:

```text
OBSERVED
PROPOSED
AUTHORIZED
EXECUTING
COMPLETED
VERIFIED
BLOCKED
FAILED
```

Unverified claims must not be merged as completed work.

## Mandatory visible connection state

The dashboard must always display the current environment connection mode. It may not be inferred by the user and must not be represented only by a color or generic “online” label.

The bridge exposes this as a **read-only system status value**. The dashboard may display it, but the user cannot edit it as a preference.

Required states:

### ONLINE

```text
MODE: ONLINE
NETWORK: CONNECTED
STATE: DEVICE LOCAL
EXTERNAL MEMORY: DISABLED
```

Network may be available. External inference is permitted only by policy and external data is allowed only through approved routes. Device-owned state remains the default.

### OFFLINE

```text
MODE: OFFLINE
NETWORK: DISCONNECTED
STATE: DEVICE LOCAL
SYNC: BLOCKED
```

External providers are unreachable or prohibited. Local AI is operational only if its local dependencies are available. State remains device-only.

### AIR-GAPPED

```text
MODE: AIR-GAPPED
NETWORK: ISOLATED
EXTERNAL ACCESS: PROHIBITED
STATE: DEVICE LOCAL
```

External communication is intentionally and enforceably prohibited. Remote inference is unavailable. State is device-local only.

The high-assurance display may additionally show:

```text
MODE: GHOST
CONNECTION: AIR-GAPPED
STATE: DEVICE LOCAL
EXTERNAL SYNC: DISABLED
```

The following distinctions are mandatory:

```text
VISIBLE CONNECTION STATE != AUTHORIZATION
ONLINE != PERMISSION
OFFLINE != SECURE BY DEFAULT
AIR-GAPPED != OWNER AUTHORITY
```

The indicator reports environment state. It does not grant capability, authorize a route, or establish identity.

Recommended terminal header:

```text
SOVEREIGNTY AI GATE
MODE: HYBRID
CONNECTION: ONLINE
STATE: DEVICE LOCAL
AUTHORITY: OWNER CONTROLLED
```

## Bridge validation rule

Before every external route, the bridge must evaluate:

```json
{
  "state_policy": {
    "required_state_location": "DEVICE_FIRST",
    "external_memory": false,
    "sync_authorized": false
  }
}
```

The route may proceed only when the destination satisfies the active policy and the owner has authorized the requested scope. The bridge must return read-only environment status separately from authorization status.

If external persistence is not authorized, the bridge must return:

```text
STATE SYNC BLOCKED
Reason: External persistence not authorized.
Data transmitted: NONE
```

The bridge must not silently retry, fall back to another destination, or claim synchronization occurred.

## Required SCAR events

### Blocked synchronization attempt

```json
{
  "event": "STATE_SYNC_ATTEMPT",
  "source": "device",
  "destination": "provider",
  "authorization": false,
  "result": "BLOCKED",
  "data_transmitted": false
}
```

### Authorized synchronization

```json
{
  "event": "STATE_SYNC",
  "scope": "conversation_summary",
  "source": "device",
  "destination": "authorized_external_store",
  "fields_transferred": [
    "completed_tasks",
    "pending_tasks"
  ],
  "fields_excluded": [
    "private_messages",
    "private_keys",
    "biometric_data"
  ],
  "authorization": true,
  "result": "COMPLETED"
}
```

Connection-state changes, blocked routes, external requests, and state movement must also be auditable with an operation identifier, timestamp, policy version, payload digest, and verification result when available.

## Frontend display requirements

SGHv119 must continuously expose:

```text
CONNECTION MODE: ONLINE / OFFLINE / AIR-GAPPED
STATE: DEVICE LOCAL ✓
HYBRID CONTINUITY: DEVICE LOCAL ✓
EXTERNAL MEMORY: DISABLED
SYNC: NOT CONFIGURED
TRAINING: NOT AUTHORIZED
AUTHORITY: OWNER CONTROLLED
```

External intelligence objects must show:

```text
PROVENANCE: EXTERNAL_PUBLIC
AUTHORIZATION: NOT EVALUATED
```

Internal governance objects must show:

```text
PROVENANCE: GOVERNANCE_VERIFIED
AUTHORIZATION: EVALUATED
```

## Continuity and hallucination-risk observability

The dashboard may display continuity and state-drift risk signals, but it must not claim that a score directly measures truth or grants authority.

Risk signals may include:

- mismatch with verified local continuity;
- contradiction with approved decisions;
- unsupported assumptions;
- missing provenance;
- failed verification checks;
- absent historical state;
- unknown external context.

Example display:

```text
AI CONTINUITY RISK
          STATE        NO STATE
Identity  LOW          HIGH
Context   LOW          MEDIUM
Claims    REVIEW       HIGH
Actions   VERIFIED     BLOCKED
```

Required distinction:

```text
HIGH CONFIDENCE != AUTHORITY
```

A risk heat map detects uncertainty. It does not authorize an action, approve a fix, or establish human identity.

## Repository governance and promotion

The governance root defines what is allowed. Implementation repositories produce controlled artifacts. Reference, development, experimental, and mirror repositories are not authorities unless explicitly promoted through the governed path.

The promotion path is:

```text
CHANGE REQUEST
  -> SIGNED COMMIT
  -> AUTOMATED TESTS
  -> SECURITY CHECKS
  -> POLICY REVIEW
  -> MERGE
  -> RELEASE EVIDENCE
```

The protected governance branch must prohibit direct pushes, require signed commits where supported, require CI and test status checks, and record provenance.

Each approved release should link:

```text
release version
commit hash
signature
test evidence
SCAR deployment record
artifact digest
```

The runtime must be able to report:

```text
RUNNING APPROVED BUILD: <version>
COMMIT: <hash>
ARTIFACT DIGEST: <digest>
EVIDENCE: <record>
```

This does not require every implementation to be placed in one monolithic repository. The required structure is:

```text
ONE GOVERNANCE ROOT
+
CONTROLLED IMPLEMENTATION REPOSITORIES
+
SIGNED ARTIFACTS
+
VERIFIED PROMOTION PATH
```

## Mode requirements

### Ghost

- device-local state only;
- no external persistence;
- no synchronization;
- no hidden network activity;
- no remote provider memory;
- local audit and SCAR only.

### Hybrid

- device-local state remains authoritative;
- synchronization is opt-in and scope-limited;
- destination, fields, retention, and result are visible;
- each synchronization event is audited and revocable.

### Online

- external execution is permitted only under explicit policy;
- credentials and destination are visible;
- external persistence remains separately controlled;
- all remote activity and state movement are auditable.

## Non-negotiable invariants

```text
DEVICE STATE IS DEFAULT
EXTERNAL STATE IS OPT-IN
HIDDEN STATE IS FORBIDDEN
UNAUTHORIZED SYNC IS BLOCKED
LOGIN != MEMORY CONSENT
NETWORK != STORAGE CONSENT
EXECUTION != OWNERSHIP
ASSISTANT != AUTHORITY
OBSERVATION != AUTHORIZATION
CODE != TRUST
BUILD != APPROVAL
```

Authentication does not grant memory consent. Network access does not grant storage consent. A provider response does not establish ownership or authorization. The assistant remains a facilitator under owner-controlled boundaries.
