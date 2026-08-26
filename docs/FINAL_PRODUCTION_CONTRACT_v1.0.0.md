# Sovereignty AI Studio — Helpers, Fixers, Watchers, and Error Handlers

## Final Production Contract v1.0.0

**Status:** Finalized / Normative

### Authority
OWNER → DEVICE IDENTITY → CANONICAL STATE → IDENTITY VERIFICATION → POLICY/GATE → EXPLICIT CAPABILITY → EXECUTION → EXECUTION RECEIPT → SCAR → OWNER-VISIBLE RESULT.

Fixers recover. Watchers observe. Neither creates authority. Execution, state, and retention are independent authorization domains.

### Canonical state
Canonical state contains authoritative identity, policy, trust anchors, configuration, cryptographic state, participant registry, and evidence infrastructure. Unverifiable canonical state fails closed. Downstream components cannot substitute for authority.

### Errors and helpers
Security-boundary errors remain distinguishable from ordinary failures. Sensitive secrets, private keys, capability/session secrets, raw prompts, private documents, and sensitive payloads never enter exception messages or evidence. Retries never bypass authorization, capability, cryptographic-integrity, or evidence-integrity failures. Fallbacks and circuit breakers cannot alter authority. Helpers are deterministic; canonical serialization is mandatory for hashes, signatures, capabilities, receipts, and SCAR; validation is not authorization; safe paths prevent traversal.

### Fixers
Fixers execute authorized recovery only. Any state-changing recovery requires an explicit capability. Fixers cannot mint authority/capabilities, change policy or trust anchors, escalate privileges, suppress evidence, or fabricate execution.

### Capability
Capabilities bind `capability_id`, issuer, subject/identity, operation, resource, context, issued/expiry times, single-use status, and lifecycle state. Operation/resource/context must match exactly. Missing, malformed, expired, revoked, consumed, or mismatched capabilities are denied. Single-use consumption is atomic and occurs before execution. Consumed/expired/revoked states are terminal. Failed execution leaves the capability consumed.

### Re-issuance
Recovery retry requires a new authority/policy decision and a new capability ID, validity window, explicit scope, failure reference, logging, and owner visibility. A previous capability is never resurrected.

### Owner visibility and triage
Runtime states distinguish `AUTHORIZED`, `EXECUTED`, `FAILED`, `RECOVERY_REQUESTED`, `REISSUED`, `RETRY_EXECUTED`, `DENIED`, and `UNKNOWN`. Triage is `TRIAGE → REPAIR PROPOSAL → OWNER APPROVAL → DENY/TERMINATE or APPROVE → NEW AUTHORIZATION → NEW CAPABILITY → REPAIR → VERIFY → RECEIPT → SCAR`.

### Model fallback
Model policy selects the replacement; ModelFixer executes only the already-authorized swap. Model family information is not authorization. A failed authorized swap cannot select another model without a new policy decision and capability.

### Watchers and evidence
Watchers observe and recommend; they cannot authorize, mint/extend/reissue capabilities, suppress/rewrite evidence, or claim execution. Mandatory processing is `EVENT → CAPTURE → EVIDENCE APPEND → ANALYSIS`. Append failure is `evidence_persistence=FAILED` and requires fail-closed or an explicitly governed evidence queue. Analysis cannot precede persistence.

### Receipts and SCAR
Every successful state-changing fixer operation requires a receipt containing `receipt_id`, `capability_id`, `operation`, `resource`, `context`, execution start/end, executed, and result. No execution → no success receipt. No receipt → no `recovery_completed`. SCAR records evidence and does not create authority. Success evidence is causally bound to the receipt.

### Evidence-store failure
Corrupted evidence storage means trust is unknown and the runtime fails closed with an owner-visible security event. Rebuild cannot fabricate historical evidence. A rebuilt store requires independent integrity verification before trust is restored.

### Normative invariants
- AUTH-001 through AUTH-008: owner authority; capability required; exact scope; terminal lifecycle; atomic single-use; no resurrection; authority-only reissuance; new capability identity.
- STATE-001/002: canonical state is authoritative; state does not imply retention.
- EXEC-001 through EXEC-005: execution does not imply state; no execution/success evidence; receipt required; actual execution binding; no implicit retry.
- RET-001/002: retention requires authorization; execution does not imply retention.
- OBS-001 through OBS-005: capture/append precedes analysis; no suppression/rewrite; failed persistence cannot become success.
- AUDIT-001 through AUDIT-004: privileged transitions evidenced; SCAR is evidence-only; success causality; reissuance independently evidenced.
- FAIL-001 through FAIL-003: corrupted evidence fails closed; unknown authorization denies/unknown; security failure cannot degrade to success.
- FIX-001 through FIX-005: fixers cannot become policy/authority; cannot resurrect capabilities; retry requires new capability; failures remain observable.
- WATCH-001 through WATCH-003: watchers cannot authorize/create/suppress.
- SOV-001 through SOV-003: recovery cannot escalate authority; operational failure cannot become authorization; absence of evidence cannot become success evidence.

### Production state machine
```text
OWNER → IDENTITY/CANONICAL STATE → POLICY/GATE → CAPABILITY
  → EXACT SCOPE/LIFECYCLE → ATOMIC CONSUME → EXECUTION
  → FAILURE RECEIPT/SCAR/OWNER OR EXECUTION RECEIPT/SCAR/OWNER
  → explicit recovery request → POLICY/GATE → new capability → execution

WATCHER: EVENT → CAPTURE → EVIDENCE APPEND → ANALYSIS → METRIC/ALERT
                     └→ FAILURE: FAIL CLOSED / GOVERNED QUEUE
```

This contract is normative. Implementations must enforce these boundaries rather than merely document them.
