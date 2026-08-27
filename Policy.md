Sovereignty AI Studio

Helpers, Fixers, Watchers, and Error Handlers

Final Production Contract

Version: 1.0.0
Status: Finalized / Normative
Scope: /errors/, /helpers/, /fixers/, /watchers/, capability-gated recovery, model fallback execution, execution receipts, SCAR evidence, and evidence-storage failure handling.

⸻

1. Purpose

This infrastructure provides four operational subsystems:

1. Errors — structured failures, retries, fallbacks, and circuit breaking.
2. Helpers — deterministic utility functions.
3. Fixers — capability-scoped recovery and self-healing.
4. Watchers — observation, monitoring, metrics, and evidence capture.

These components are not an authority plane.

The governing boundary is:

OWNER AUTHORITY
      │
      ▼
IDENTITY / CANONICAL STATE
      │
      ▼
POLICY / AUTHORITY GATE
      │
      ▼
EXPLICIT CAPABILITY
      │
      ▼
EXECUTION BOUNDARY
      │
      ├──────────────► FIXERS
      │                 execute authorized recovery
      │
      └──────────────► WATCHERS
                        observe
                             
EXECUTION
      │
      ▼
EXECUTION RECEIPT
      │
      ▼
SCAR EVIDENCE
      │
      ▼
OWNER-VISIBLE RESULT

The architecture therefore preserves the core rule:

Fixers recover. Watchers observe. Neither creates authority.

The underlying sovereignty model also requires execution, state, and retention to remain independent authorization domains. Branch · AI ML UL Architecture.txt

⸻

2. Identity and Canonical State Boundary

The authority pipeline begins above the policy gate.

OWNER AUTHORITY
      │
      ▼
DEVICE IDENTITY
      │
      ▼
CANONICAL STATE
      │
      ▼
IDENTITY VERIFICATION
      │
      ▼
AUTHORITY / POLICY GATE
      │
      ▼
CAPABILITY

Canonical runtime state includes the authoritative security state required to operate the platform, including identity, policy, trust anchors, configuration, cryptographic state, participant registry, and evidence infrastructure.

If canonical state cannot be verified:

CANONICAL STATE INVALID
        │
        ▼
     FAIL CLOSED

The dashboard, watcher, fixer, or model layer cannot substitute for canonical authority.

The architecture explicitly distinguishes identity from authorization: an authenticated actor is not automatically authorized to perform an operation. Branch · Branch · Branch · Branch · Branch · Branch · Branch · GitHub Actions Qu.txt

⸻

3. Authority Boundary

Only the authority/policy layer may:

* determine authorization;
* issue capabilities;
* revoke capabilities;
* re-issue capabilities;
* modify authorization policy;
* establish authority scope.

No fixer, watcher, model, connector, orchestrator, retry handler, or fallback handler may perform any of those functions.

IDENTITY
    ≠
AUTHENTICATION
    ≠
AUTHORIZATION
    ≠
EXECUTION
    ≠
EVIDENCE

Authorization data also cannot become an identity authority. Branch · iPhone 17 App Optimization.txt

⸻

4. Errors Module

Located at:

/errors/

Custom exceptions

from errors import (
    SovereigntyError,
    BridgeError,
    MemoryError,
    TokenError,
    AIModelError,
    WatcherError,
    ValidationError,
    ConfigurationError,
    NetworkError,
    TimeoutError,
)

Security-boundary errors should remain distinguishable from ordinary operational failures.

Sensitive information must never be placed into exception messages or evidence:

credentials
private keys
capability secrets
session secrets
raw prompts
private documents
sensitive payloads

⸻

5. Error Handlers

from errors import (
    ErrorHandler,
    RetryHandler,
    FallbackHandler,
    CircuitBreaker,
)

Error tracking

handler = ErrorHandler()
handler.handle(
    error,
    context="operation name",
)

Retry

retry_handler = RetryHandler(
    max_retries=3,
    base_delay=1.0,
)
result = await retry_handler.execute(
    async_function,
    context="retry operation",
)

Retries are operational mechanisms only.

They cannot retry:

authorization denial
capability failure
policy denial
expired capability
consumed capability
cryptographic integrity failure
evidence-integrity failure

A consumed single-use capability is never implicitly restored by a retry handler.

⸻

6. Fallback

fallback_handler = FallbackHandler(
    fallback="default value",
)
result = await fallback_handler.execute(
    async_function,
    context="fallback operation",
)

A fallback value must not silently alter authorization state.

For model/provider fallback, the replacement must already have been selected and authorized by the policy gate.

⸻

7. Circuit Breaker

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
)
result = await breaker.execute(
    async_function,
)

A circuit breaker controls availability.

It cannot:

issue capability
extend capability
reissue capability
modify policy
modify identity
grant privileges

⸻

8. Error Decorators

from errors import (
    handle_errors,
    retry_on_failure,
    fallback_on_error,
    log_errors,
)

Example:

@handle_errors(
    retry=True,
    max_retries=3,
    fallback="default response",
)
async def robust_operation():
    ...

Decorators never bypass the authority or evidence boundaries.

⸻

9. Helpers Module

Located at:

/helpers/

Helpers provide deterministic utility functionality.

They do not make policy decisions.

JSON

from helpers import (
    safe_json_loads,
    safe_json_dumps,
    json_to_dict,
    dict_to_json,
)

Canonical serialization must be used wherever serialized data participates in:

hashes
signatures
capabilities
execution receipts
SCAR evidence

⸻

Messages

from helpers import (
    format_ws_message,
    parse_ws_message,
    create_response,
    create_error_response,
)

Malformed messages must fail validation before processing.

⸻

Hashing

from helpers import (
    sha256,
    sha3_512,
    calculate_checksum,
    verify_checksum,
)

A digest establishes integrity.

It does not establish:

identity
authority
authorization
execution

⸻

Validation

from helpers import (
    validate_message_type,
    validate_session_id,
    validate_agent_name,
    sanitize_input,
)

Validation is not authorization.

⸻

Time

from helpers import (
    current_timestamp_ms,
    format_timestamp,
    time_since,
)

Capability expiry must use a trusted and consistently defined time source.

⸻

Paths

from helpers import (
    ensure_dir,
    safe_path_join,
    get_data_dir,
    get_logs_dir,
)

safe_path_join() must prevent traversal outside the authorized base.

⸻

10. Fixers Module

Located at:

/fixers/

Fixers provide authorized recovery execution.

They may:

retry an authorized operation
reconnect
restore authorized operational state
repair authorized state
execute an authorized model swap
verify results
produce execution receipts

They may not:

mint authority
mint capabilities
select unauthorized policy
modify root authority
modify trust anchors
modify authorization policy
escalate permissions
suppress evidence
fabricate execution

The integration architecture follows the same principle: execution mechanisms remain downstream of policy/capability resolution. Branch · AI ML UL Architecture.txt

⸻

11. Mandatory Recovery Capability

Any fixer operation that changes state MUST receive an explicit capability from the authority gate.

This is a hard precondition.

if capability is None:
    raise RecoveryCapabilityError(
        "Explicit recovery capability required"
    )

This is insufficient:

if policy_allows:
    fix()

The execution boundary requires an actual capability artifact.

⸻

12. Capability Scope

A capability must be bound to at least:

capability_id
issuer
subject / identity
operation
resource
context
issued_at
expires_at
single_use
lifecycle state

The execution request must match the capability exactly:

TOKEN.operation == REQUEST.operation
TOKEN.resource  == REQUEST.resource
TOKEN.context   == REQUEST.context

Any mismatch is denial.

operation A token
        ≠
operation B request
resource A token
        ≠
resource B request
context A token
        ≠
context B request

A fixer cannot reinterpret a token.

⸻

13. Capability Lifecycle

                 ISSUED
                   │
                   ▼
                 VALID
                   │
             ┌─────┴─────┐
             │           │
             ▼           ▼
          CONSUMED     EXPIRED

Terminal states cannot be reversed:

CONSUMED → VALID       prohibited
EXPIRED  → VALID       prohibited
REVOKED  → VALID       prohibited

⸻

14. Atomic Single-Use Consumption

Single-use capability consumption must be atomic.

Conceptually:

async def consume_capability(token):
    async with capability_store.atomic():
        current = await capability_store.get(token.id)
        if current is None:
            raise RecoveryCapabilityError("Unknown capability")
        if current.revoked:
            raise RecoveryCapabilityError("Capability revoked")
        if current.expired():
            raise RecoveryCapabilityError("Capability expired")
        if current.consumed:
            raise RecoveryCapabilityError("Capability already consumed")
        await capability_store.mark_consumed(token.id)

Concurrent attempts using the same token must produce:

one successful consumption
zero additional successful consumptions

A non-atomic check-then-set implementation is prohibited.

⸻

15. Consume-Then-Execute

The authoritative lifecycle is:

CAPABILITY
    │
    ▼
VERIFY
    │
    ▼
EXACT SCOPE CHECK
    │
    ▼
LIFECYCLE CHECK
    │
    ▼
ATOMIC CONSUMPTION
    │
    ▼
EXECUTION
    │
    ▼
EXECUTION RECEIPT

Consumption occurs before execution.

Therefore a failed execution does not make the capability reusable.

This intentionally eliminates token replay through execution failure.

⸻

16. Execution Failure

If execution fails:

CAPABILITY CONSUMED
        │
        ▼
EXECUTION FAILED
        │
        ├── NO SUCCESS EVIDENCE
        │
        ├── FAILURE RECEIPT
        │
        ▼
OWNER-VISIBLE FAILURE

There is no implicit retry.

The fixer cannot resurrect the consumed capability.

⸻

17. Explicit Capability Re-Issuance

A subsequent attempt requires a new authorization path:

EXECUTION FAILURE
        │
        ▼
FAILURE EVIDENCE
        │
        ▼
RECOVERY REQUEST
        │
        ▼
AUTHORITY / POLICY GATE
        │
        ├── DENY
        │
        └── RE-ISSUE
               │
               ▼
        NEW CAPABILITY ID
               │
               ▼
           EXECUTION

Re-issuance:

* can only originate at the authority boundary;
* creates a new capability ID;
* has a new validity window;
* contains explicit scope;
* references the failed execution;
* is logged;
* is owner-visible.

It is a new authorization, never resurrection of the previous token.

⸻

18. Re-Issuance Evidence

Failure:

{
  "event_type": "recovery_execution_failed",
  "capability_id": "cap-001",
  "execution_receipt_id": "receipt-001",
  "operation": "database.repair",
  "result": "FAILED"
}

Authorized re-issuance:

{
  "event_type": "capability_reissued",
  "previous_capability_id": "cap-001",
  "new_capability_id": "cap-002",
  "reason": "authorized recovery retry",
  "authorization_reference": "auth-002"
}

New execution:

cap-002
   ↓
execution
   ↓
receipt-002
   ↓
SCAR

⸻

19. Owner Visibility

The owner-visible state must distinguish:

AUTHORIZED
EXECUTED
FAILED
RECOVERY_REQUESTED
REISSUED
RETRY_EXECUTED
DENIED
UNKNOWN

It must never collapse execution failure and subsequent authorization into an unexplained automatic success.

⸻

20. Connection Fixer

from fixers import ConnectionFixer
fixer = ConnectionFixer(
    max_retries=5,
    retry_delay=2.0,
)
success = await fixer.fix_connection(
    connect_func,
    test_func,
)
await fixer.ensure_connected(
    connect_func,
    is_connected_func,
)

A connection fixer can restore an already-authorized connection.

It cannot silently change:

destination
provider
transport
network mode
runtime mode

⸻

21. Database Fixer

from fixers import DatabaseFixer
fixer = DatabaseFixer(
    db_path,
    schema,
)
is_healthy, issues = fixer.check_integrity()
backup_path = fixer.create_backup()
success = await fixer.fix_database()
fixer.vacuum_database()

Recovery sequence:

CHECK
  ↓
BACKUP
  ↓
REPAIR
  ↓
VERIFY
  │
  ├── FAIL → FAIL CLOSED
  │
  └── PASS
       ↓
     COMMIT
       ↓
EXECUTION RECEIPT
       ↓
     SCAR

⸻

22. Evidence Store Fail-Closed Rule

This is non-negotiable.

CORRUPTED EVIDENCE STORE
          │
          ▼
      TRUST = NO
          │
          ▼
      FAIL CLOSED
          │
          ▼
OWNER-VISIBLE SECURITY EVENT

A rebuilt evidence store is not automatically trustworthy.

Reconstruction may restore operational capacity, but it cannot manufacture historical evidence that was lost or corrupted.

Independent integrity verification is required before a rebuilt store can be trusted for subsequent evidence operations.

This is consistent with the established SCAR model: evidence records provenance and integrity; it does not become trustworthy merely because storage was reconstructed. Branch · SCAREvent Patch Review.txt

⸻

23. Configuration Fixer

from fixers import ConfigFixer
fixer = ConfigFixer()
is_valid, issues = fixer.validate_config(config)
fixed_config = fixer.fix_config(config)
config = fixer.fix_env_config()
fixer.ensure_config_file(config_path)

Automatic configuration repair cannot silently modify:

root authority
identity
trust anchors
authorization policy
signing keys
cryptographic requirements

Those require their own authorization paths.

⸻

24. Model Fixer

The ModelFixer is an execution component, not a model-policy engine.

Prohibited

The fixer must not select a fallback model itself:

# PROHIBITED
model_fixer.register_fallback(
    "claude",
    "gpt-5.6",
)
model_fixer.fix_model_selection(
    "claude-3-opus",
    available_models,
)

That would make the fixer an implicit routing/policy authority.

Correct flow

The authority gate determines and authorizes the replacement first:

MODEL FAILURE
     │
     ▼
WATCHER / HEALTH OBSERVATION
     │
     ▼
MODEL ROUTING / POLICY GATE
     │
     ├── DENY
     │
     └── AUTHORIZE GPT-5.6
              │
              ▼
       CAPABILITY ISSUED
              │
              ▼
       MODEL FIXER EXECUTES
              │
              ▼
       EXECUTION RECEIPT
              │
              ▼
             SCAR

Example:

from fixers import ModelFixer
model_fixer = ModelFixer()
# The gate, not ModelFixer, selected GPT-5.6.
capability = await authority_gate.issue_capability(
    operation="model.swap",
    resource="model/claude-3-opus",
    context={
        "replacement_model": "gpt-5.6",
        "reason": "authorized-fallback",
    },
)
# ModelFixer executes only the explicitly authorized swap.
result = await model_fixer.execute_authorized_swap(
    current_model="claude-3-opus",
    replacement_model="gpt-5.6",
    capability=capability,
)

The division is:

GATE
    decides what is authorized
CAPABILITY
    defines what may execute
MODEL FIXER
    executes exactly that operation

Model-family identification remains informational:

family = model_fixer.get_model_family("gpt-5.6")

Returning:

gpt

does not authorize every GPT model.

⸻

25. Model Failure Recovery

If the authorized GPT-5.6 swap fails:

capability
    ↓
atomic consumption
    ↓
GPT-5.6 swap
    ↓
failure

The fixer cannot automatically choose another model.

The next attempt requires:

failure evidence
      ↓
policy evaluation
      ↓
new authorization
      ↓
new capability
      ↓
new execution

This preserves the single-use capability lifecycle.

⸻

26. Health Monitor

from fixers import HealthMonitor
monitor = HealthMonitor(
    check_interval=60.0,
    auto_fix=True,
)
monitor.register_health_check(
    "database",
    check_db_health,
    fix_db,
)
monitor.register_health_check(
    "connection",
    check_conn_health,
    fix_conn,
)
await monitor.start_monitoring()

auto_fix=True means:

invoke an already-authorized recovery path when its capability requirements are satisfied.

It does not mean:

authorize whatever recovery a fixer decides to perform.

⸻

27. Watchers Module

Located at:

/watchers/

Watchers observe.

They may:

measure
classify
aggregate
alert
recommend
capture evidence

They may not:

authorize
mint capabilities
extend capabilities
reissue capabilities
suppress evidence
rewrite evidence
claim execution

Council/watchers similarly produce evidence or evaluation; policy remains the authorization source. The whole completionApp.md

⸻

28. Evidence Observation Boundary

Mandatory watcher processing follows:

RUNTIME EVENT
      │
      ▼
CAPTURE
      │
      ▼
EVIDENCE APPEND
      │
      ▼
ANALYSIS
      │
      ▼
METRIC / ALERT / RECOMMENDATION

Capture → append → analyze is mandatory.

Analysis must not precede evidence persistence.

⸻

29. Evidence Sink Failure

If persistence fails:

CAPTURE
   ↓
APPEND
   ↓
FAIL

the watcher must not report:

persisted = true

It must report the actual state:

evidence_persistence = FAILED

For mandatory evidence, the runtime must fail closed or enter an explicitly governed evidence queue.

This eliminates the silent-drop condition in which analysis continues while the system falsely claims that evidence was persisted.

⸻

30. Watcher Non-Suppression

A watcher cannot:

delete an observed event
drop an observed event
rewrite observed evidence
suppress mandatory evidence
intentionally delay mandatory evidence
mark failed persistence as success

The watcher analyzes evidence after the evidence boundary has been crossed.

⸻

31. AI Model Watcher

from watchers import AIModelWatcher
from fixers import ModelFixer
model_fixer = ModelFixer()
watcher = AIModelWatcher(
    event_bus,
    model_fixer,
)
await watcher.start()
status = watcher.status()

The watcher may observe model failures and provide routing information.

It does not grant the resulting model capability.

A model recommendation is not an authorization decision.

⸻

32. Medical AI Watcher

from watchers import MedicalAIWatcher
watcher = MedicalAIWatcher(
    event_bus,
)
await watcher.start()
performance = watcher.get_model_performance(
    "medical-classifier-v1",
)
compliance = watcher.get_compliance_summary()
status = watcher.status()

Observed compliance metrics describe evidence.

They must not be interpreted as an unconditional guarantee of compliance.

⸻

33. Execution / State / Retention Separation

These are independent authorization domains.

EXECUTION AUTHORIZATION
        │
        └── may perform operation
STATE AUTHORIZATION
        │
        └── may modify state
RETENTION AUTHORIZATION
        │
        └── may retain data

Therefore:

EXECUTE ≠ WRITE STATE
WRITE STATE ≠ RETAIN
EXECUTE ≠ RETAIN

The broader architecture explicitly requires this separation. Branch · AI ML UL Architecture.txt

For external operations, the authorization path is:

Request
  ↓
Destination
  ↓
Capability
  ↓
State Permission
  ↓
Retention Permission
  ↓
Owner Approved Action
  ↓
Execution
  ↓
Evidence

Branch · AI ML UL Architecture.txt

⸻

34. Execution Receipt

Every state-changing fixer operation that reports success must produce an execution receipt.

Minimum conceptual fields:

receipt_id
capability_id
operation
resource
context
execution_start
execution_end
executed
result

The receipt must describe the actual operation.

⸻

35. Success Evidence

The only valid recovery-success chain is:

CAPABILITY
    ↓
EXACT SCOPE VALIDATION
    ↓
ATOMIC CONSUMPTION
    ↓
EXECUTION
    ↓
EXECUTION RECEIPT
    ↓
SCAR recovery_completed

This is invalid:

FIXER FUNCTION RETURNED
    ↓
recovery_completed

Function completion alone is not execution evidence.

⸻

36. SCAR Contract

SCAR records evidence.

It does not create authority.

Example:

{
  "event_type": "recovery_completed",
  "capability_id": "cap-002",
  "execution_receipt_id": "receipt-002",
  "operation": "database.repair",
  "resource": "database/main",
  "context": "authorized-recovery",
  "result": "SUCCESS"
}

The event must be causally bound to the corresponding execution receipt.

SCAR remains evidence rather than a policy engine. The architecture likewise specifies that privileged transitions produce evidence while policy/capability resolution precedes execution. Branch · AI ML UL Architecture.txt

⸻

37. Security Test Contract

Identity / authority

✓ invalid canonical state → FAIL CLOSED
✓ unverified identity → DENY
✓ authentication does not imply authorization
✓ fixer cannot become authority
✓ watcher cannot become authority

Capability

✓ no capability → DENY
✓ malformed capability → DENY
✓ expired capability → DENY
✓ revoked capability → DENY
✓ consumed capability → DENY
✓ wrong operation → DENY
✓ wrong resource → DENY
✓ wrong context → DENY

Replay

✓ single-use token cannot be replayed
✓ concurrent reuse allows one successful consumption
✓ concurrent reuse cannot produce two executions
✓ consumed token cannot return to VALID
✓ expired token cannot be reused
✓ revoked token cannot be reused

Cross-domain scope

✓ operation A token cannot execute operation B
✓ resource A token cannot execute resource B
✓ context A token cannot execute context B
✓ execution permission does not imply state permission
✓ state permission does not imply retention permission

Failed execution

✓ token remains consumed after execution failure
✓ failed execution cannot emit success
✓ failed execution produces failure evidence
✓ failed execution cannot trigger implicit retry
✓ fixer cannot resurrect consumed capability

Re-issuance

✓ re-issuance requires authority boundary
✓ re-issuance creates a new capability ID
✓ old capability remains consumed
✓ re-issuance is logged
✓ re-issuance is owner-visible
✓ re-issued capability has explicit operation
✓ re-issued capability has explicit resource
✓ re-issued capability has explicit context
✓ re-issued capability has explicit expiry
✓ unauthorized re-issuance is denied

Model fallback

✓ fixer cannot select unauthorized replacement
✓ GPT-5.6 swap requires gate authorization
✓ model family does not imply model authorization
✓ failed GPT-5.6 swap cannot silently select another model
✓ subsequent model attempt requires new authorization
✓ subsequent model attempt requires new capability

Execution receipts

✓ no execution → no success receipt
✓ no receipt → no recovery_completed
✓ receipt operation matches execution
✓ receipt resource matches execution
✓ receipt context matches execution
✓ receipt capability matches execution

Watchers

✓ watcher cannot suppress event
✓ watcher cannot delete event
✓ watcher cannot rewrite event
✓ watcher cannot intentionally delay mandatory evidence
✓ capture precedes append
✓ append precedes analysis
✓ failed append cannot be reported as success

Evidence store

✓ corrupted evidence store → FAIL CLOSED
✓ rebuilt evidence store → untrusted until independently verified
✓ historical evidence cannot be fabricated during rebuild
✓ evidence integrity failure is owner-visible

⸻

38. Normative Invariants

AUTH

AUTH-001
Owner identity is the authority root.
AUTH-002
No valid capability means no state-changing recovery.
AUTH-003
Operation, resource, and context must match exactly.
AUTH-004
Expired, revoked, or consumed capability → DENY.
AUTH-005
Single-use capability cannot be replayed.
AUTH-006
A consumed capability cannot be implicitly restored.
AUTH-007
Capability re-issuance requires the authority boundary.
AUTH-008
Re-issued capability receives a new identity and lifecycle.

STATE

STATE-001
Canonical state is device authoritative.
STATE-002
State permission does not imply retention permission.

EXEC

EXEC-001
Execution permission does not imply state permission.
EXEC-002
No execution means no success evidence.
EXEC-003
No execution receipt means no recovery_completed event.
EXEC-004
Success evidence must identify the actual execution.
EXEC-005
Failed execution cannot trigger an implicit retry.

RETENTION

RET-001
Retention requires explicit authorization.
RET-002
Execution does not imply retention.

OBSERVATION

OBS-001
Mandatory observation crosses the evidence boundary before analysis.
OBS-002
Watchers cannot suppress observed events.
OBS-003
Watchers cannot rewrite observed evidence.
OBS-004
Evidence append failure cannot become persisted success.
OBS-005
Watcher analysis cannot determine that failed persistence succeeded.

AUDIT

AUDIT-001
Every privileged transition produces evidence.
AUDIT-002
SCAR records evidence; SCAR does not create authority.
AUDIT-003
Success evidence is causally bound to an execution receipt.
AUDIT-004
Capability re-issuance is independently evidenced.

FAILURE

FAIL-001
Corrupted evidence storage → FAIL CLOSED.
FAIL-002
Unknown authorization state → DENY or UNKNOWN.
FAIL-003
Security-boundary failure cannot silently degrade into success.

FIXER

FIX-001
Fixers cannot become a policy engine.
FIX-002
Fixers cannot mint authority.
FIX-003
Fixers cannot resurrect consumed capabilities.
FIX-004
Recovery retry requires newly authorized capability.
FIX-005
Recovery failure remains observable.

WATCHER

WATCH-001
Watchers cannot become an authority engine.
WATCH-002
Watchers cannot create capabilities.
WATCH-003
Watchers cannot suppress mandatory evidence.

SOVEREIGNTY

SOV-001
No recovery path may escalate authority.
SOV-002
No component may convert operational failure into authorization.
SOV-003
No component may convert absence of evidence into evidence of success.

⸻

39. Final Production State Machine

                         OWNER
                           │
                           ▼
                IDENTITY / CANONICAL STATE
                           │
                           ▼
                     POLICY / GATE
                           │
                           ▼
                  CAPABILITY ISSUED
                           │
                           ▼
             EXACT SCOPE + LIFECYCLE CHECK
                           │
                  ┌────────┴────────┐
                  │                 │
                DENY              VALID
                  │                 │
                  ▼                 ▼
                SCAR          ATOMIC CONSUME
                                    │
                                    ▼
                                EXECUTION
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                       FAIL                  SUCCESS
                         │                     │
                         ▼                     ▼
                  FAILURE RECEIPT       EXECUTION RECEIPT
                         │                     │
                         ▼                     ▼
                       SCAR                  SCAR
                         │
                         ▼
                 OWNER-VISIBLE FAILURE
                         │
                         ▼
              EXPLICIT RECOVERY REQUEST
                         │
                         ▼
                     POLICY / GATE
                         │
                   ┌─────┴─────┐
                   │           │
                 DENY        RE-ISSUE
                               │
                               ▼
                         NEW CAPABILITY
                               │
                               ▼
                           EXECUTION

Watcher processing remains separate:

RUNTIME EVENT
      │
      ▼
   CAPTURE
      │
      ▼
EVIDENCE APPEND
      │
      ├── FAILURE → FAIL CLOSED / GOVERNED QUEUE
      │
      ▼
   ANALYSIS
      │
      ▼
 METRIC / ALERT

⸻

40. Final Contract

The production invariant is:

A fixer may recover only through an explicitly issued, exactly scoped, valid capability. A single-use capability is atomically consumed before execution and can never be replayed or implicitly restored. A failed execution produces failure evidence and does not authorize another attempt. Any subsequent attempt requires a newly issued capability through the authority boundary, with a new capability ID, explicit scope, explicit validity, logging, and owner visibility. Successful recovery evidence requires a causally corresponding execution receipt. Model fallback selection belongs to the authority/policy gate; ModelFixer executes only the already-authorized swap, including GPT-5.6. Watchers capture and append evidence before analysis and cannot suppress, rewrite, delay, or falsely report mandatory evidence. Corrupted evidence storage fails closed. Execution, state, and retention remain independent authorization domains.

The resulting separation is:

IDENTITY
    → establishes who
CANONICAL STATE
    → establishes authoritative device state
GATE
    → decides what is permitted
CAPABILITY
    → constrains what may execute
FIXER
    → executes authorized recovery
WATCHER
    → observes
EXECUTION RECEIPT
    → establishes what actually executed
SCAR
    → records evidence
OWNER
    → retains ultimate authority

That is the finalized contract. It keeps self-healing inside the delegated security boundary rather than allowing recovery infrastructure to evolve into a second policy engine. 
