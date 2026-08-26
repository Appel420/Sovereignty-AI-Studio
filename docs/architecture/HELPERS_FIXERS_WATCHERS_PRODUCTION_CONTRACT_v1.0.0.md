# Helpers, Fixers, Watchers, and Error Handlers — Final Production Contract

**Version:** 1.0.0  
**Status:** Finalized / Normative

## Boundary

```text
OWNER AUTHORITY
      ↓
IDENTITY / CANONICAL STATE
      ↓
POLICY / AUTHORITY GATE
      ↓
EXPLICIT CAPABILITY
      ↓
EXECUTION BOUNDARY
      ├── FIXERS  → authorized recovery
      └── WATCHERS → observation

EXECUTION → EXECUTION RECEIPT → SCAR → OWNER-VISIBLE RESULT
```

Fixers recover. Watchers observe. Neither creates authority.

## Mandatory invariants

- Invalid canonical state fails closed.
- Identity, authentication, authorization, execution, and evidence remain separate.
- State-changing fixer operations require an explicitly issued capability.
- Capability operation, resource, and context must match exactly.
- Expired, revoked, or consumed capabilities are denied.
- Single-use consumption is atomic and occurs before execution.
- Failed execution does not restore or implicitly retry a consumed capability.
- Subsequent recovery requires a new authority decision and a new capability ID.
- Successful recovery requires a causally corresponding execution receipt before `recovery_completed` evidence.
- Model fallback selection belongs to the policy/authority gate; `ModelFixer` only executes an already-authorized swap.
- Watchers must capture and append evidence before analysis.
- Evidence persistence failure cannot be reported as success; mandatory evidence failure is fail-closed or explicitly governed by an evidence queue.
- Corrupted evidence storage is untrusted and fails closed until independently verified.
- Execution, state, and retention are independent authorization domains.

## Recovery state machine

```text
CAPABILITY
  ↓
VERIFY + EXACT SCOPE
  ↓
ATOMIC CONSUMPTION
  ↓
EXECUTION
  ├─ FAIL → FAILURE RECEIPT → SCAR → explicit recovery request → GATE → new capability
  └─ PASS → EXECUTION RECEIPT → SCAR recovery_completed
```

## Re-issuance

Re-issuance can only originate at the authority boundary. It creates a new capability ID, validity window, explicit operation/resource/context, authorization reference, audit record, and owner-visible state. The previous capability remains consumed.

## Watcher evidence boundary

```text
RUNTIME EVENT → CAPTURE → EVIDENCE APPEND → ANALYSIS → METRIC / ALERT / RECOMMENDATION
```

A watcher cannot authorize, mint/reissue/extend capabilities, suppress/delete/rewrite mandatory evidence, or claim failed persistence succeeded.

## Model fallback

The policy gate selects and authorizes the replacement model. The fixer executes exactly the authorized swap. Model-family identification is informational and never implies authorization for every model in that family.

## Owner-visible states

`AUTHORIZED`, `EXECUTED`, `FAILED`, `RECOVERY_REQUESTED`, `REISSUED`, `RETRY_EXECUTED`, `DENIED`, `UNKNOWN`.

## Acceptance

The associated test suite must cover capability denial and lifecycle, atomic single-use replay resistance, failed execution, explicit re-issuance, model fallback authorization, execution receipts, watcher non-suppression, evidence ordering/persistence failure, corrupted evidence-store fail-closed behavior, and execution/state/retention separation.
