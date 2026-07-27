# Device State Sovereignty Policy v1.1.1

**Status:** Authoritative behavioral and state-governance contract  
**Scope:** SGHv119 dashboard, local device bridge, Hybrid continuity, agent sessions, external inference, synchronization, audit, and SCAR evidence.

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

The default and authoritative state class. It includes:

- conversations and per-agent session files;
- Hybrid continuity records;
- session checkpoints;
- agent state;
- approvals and owner decisions;
- task history;
- local repository and workspace context;
- local audit and SCAR evidence;
- owner preferences.

**Control:** owner-controlled and device-local.

### EXTERNAL_EPHEMERAL

Allowed only for an explicitly approved execution. The permitted flow is:

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

Blocked by default. It requires all of the following:

- explicit owner authorization;
- named destination;
- visible fields to be transferred;
- declared retention policy;
- revocation path;
- audit and SCAR event;
- successful verification of the result.

## Hybrid continuity

Hybrid is a device-local aggregate continuity layer. It combines verified records from each agent without moving authority to an external provider.

```text
Per-agent DEVICE_LOCAL records
  -> device-local Hybrid continuity file
  -> SGHv119 dashboard resume state
```

The Hybrid record must preserve the who, what, when, where, why, and how of verified work across the day, week, month, and year.

Per-agent detailed records remain authoritative for their individual conversations. The Hybrid file is the device-local aggregate used to resume work across agents and sessions. External providers never become the continuity source.

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

The route may proceed only when the destination satisfies the active policy and the owner has authorized the requested scope.

If external persistence is not authorized, the bridge must return:

```text
STATE SYNC BLOCKED
Reason: External persistence not authorized.
Data transmitted: NONE
```

The bridge must not silently retry, fall back to another destination, or claim that synchronization occurred.

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

The event must also include a request or operation identifier, timestamp, policy version, payload digest, and verification result when those fields are available.

## Frontend display requirements

SGHv119 must continuously expose the location and policy state:

```text
STATE:
DEVICE LOCAL ✓

HYBRID CONTINUITY:
DEVICE LOCAL ✓

EXTERNAL MEMORY:
DISABLED

SYNC:
NOT CONFIGURED

TRAINING:
NOT AUTHORIZED
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

The dashboard must distinguish observation, recommendation, authorization, execution, and verification. It must never report completion from an attempt alone.

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
```

Authentication does not grant memory consent. Network access does not grant storage consent. A provider response does not establish ownership or authorization. The assistant remains a facilitator under owner-controlled boundaries.
