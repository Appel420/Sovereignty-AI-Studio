# Sovereign Intelligence Architecture (SIA)

## RFC Suite v1.0 — Consolidated Specification

**Status:** Draft Foundation Release  
**Canonical RFC mapping:** This document supersedes conflicting draft mappings of
RFC-0001 through RFC-0013.

## Architecture Principle

Nothing is trusted because it exists. It is trusted only after it has been
validated, canonicalized, identified, authorized, context-bound,
capability-approved, policy-approved, executed, recorded, verified, and bound
to evidence.

## Authority Flow

```text
RFC-0001 Trust Boundary and Envelope
  -> RFC-0003 Canonical Serialization
  -> RFC-0002 Identity and Authorization
  -> RFC-0004 Capability Negotiation
  -> RFC-0005 Identity Keys and Cryptographic Binding
  -> RFC-0006 Policy Engine and Decision Evaluation
  -> RFC-0007 Provenance Ledger
  -> RFC-0008 Session Lifecycle and Secure Cleanup
  -> RFC-0009 Conformance and Interoperability
  -> RFC-0010 Artifact Binding Authority
  -> RFC-0011 Governance and Registry Authority
  -> RFC-0012 Trust Federation and External Authority Bridges
  -> RFC-0013 Sovereign Execution Boundary
```

Each layer MUST preserve the authority constraints imposed by every preceding
layer. Availability, observation, metadata, provider claims, and presentation
state MUST NOT independently create authority.

---

## RFC-0001 — Trust Boundary and Envelope

**Status:** Frozen  
**Purpose:** Define the boundary between untrusted transport data and trusted
protocol objects.

### Primary Invariant

Raw bytes MUST NOT directly create protocol objects.

### Required Pipeline

```text
Raw bytes
  -> UTF-8 validation
  -> duplicate-key detection
  -> JSON parsing
  -> canonical validation hook
  -> ValidatedDocument
  -> envelope validation
  -> payload validation
```

```text
ValidatedDocument {
  raw_bytes
  parsed_object
}
```

A `ValidatedDocument` MUST be immutable, MUST be derived only from validated
bytes, and MUST preserve the original input bytes. A protocol object MUST
originate from a `ValidatedDocument`.

### Failure Registry

- `sia.error.invalid_utf8`
- `sia.error.duplicate_key`
- `sia.error.malformed_json`
- `sia.error.non_canonical`
- `sia.error.missing_envelope`
- `sia.error.unsupported_version`
- `sia.error.unknown_kind`

RFC-0001 owns wire validation, envelope structure, object boundaries,
extension rules, and version-negotiation boundaries. It does not define
identity, authorization, cryptography, execution, or provenance.

---

## RFC-0002 — Identity and Authorization

**Status:** Frozen  
**Primary Invariant:** No field has authority until explicitly classified.

Every field MUST declare exactly one applicable authority class:

- identity-bearing
- authorization-bearing
- integrity-bearing
- presentation-only
- operational

Identity-bearing examples include `grant_id`, `user_id`, `project_id`,
`provider`, `allowed_models`, and `expires_at`. Labels, comments, display
names, latency, and retry counts are non-authoritative unless another RFC
explicitly classifies them otherwise.

Two objects are identity-equivalent only when all identity-bearing fields
produce identical RFC-0003 canonical bytes.

Authorization evaluation MAY include subject, project, and provider identities;
allowed capabilities and models; and validity windows. It MUST NOT depend on
UI metadata, runtime behavior, provider preference, or hidden assumptions.

---

## RFC-0003 — Canonical Serialization

**Status:** Frozen  
**Primary Invariant:** Equivalent protocol objects MUST produce identical bytes.

Canonical representations MUST use:

- UTF-8 encoding;
- Unicode NFC normalization;
- canonical JSON with deterministically sorted object keys;
- no insignificant whitespace;
- deterministic array ordering where arrays are protocol-significant;
- RFC3339 UTC timestamps; and
- restricted, deterministic numeric representations.

```text
Object -> canonical bytes -> hash -> signature / identity
```

Identity, signatures, provenance, and artifact binding MUST use canonical
bytes at their hash boundary.

---

## RFC-0004 — Capability Negotiation

**Status:** Frozen  
**Primary Invariant:** An undeclared capability does not exist.

```text
Declared capability + provider declaration + authorized grant
  = permitted capability use
```

```text
CapabilityManifest {
  provider_id
  manifest_version
  capabilities
  supported_models
  constraints
  security_requirements
}
```

Providers MUST NOT dynamically invent capabilities, infer capabilities from
observed behavior, or bypass manifest declaration. Unknown optional
capabilities MUST be ignored; unknown required capabilities MUST be rejected.
An available capability is not necessarily a permitted capability.

---

## RFC-0005 — Identity Keys and Cryptographic Binding

**Status:** Draft  
**Purpose:** Define cryptographic identity relationships.

This RFC defines identity keys, signing identities, verification chains, key
lifecycle, key rotation, and binding relationships. A cryptographic key proves
control of an identity binding; it does not independently prove authorization.

```text
Key validity != permission
Key validity + authorization = allowed action
```

This RFC does not define user creation, hardware implementation, or mandatory
cryptographic algorithms.

---

## RFC-0006 — Policy Engine and Decision Evaluation

**Status:** Draft  
**Primary Invariant:** Policy decisions MUST be derived from classified inputs
only.

Permitted policy inputs are identity state, authorization grants, capability
state, session state, and security requirements. A policy decision object MUST
produce one of:

- `ALLOW`
- `DENY`
- `REQUIRE_CONSENT`
- `QUARANTINE`

Policy engines MUST NOT use reputation alone, UI metadata, undocumented
provider behavior, or hidden state as decision inputs.

---

## RFC-0007 — Provenance Ledger

**Status:** Frozen  
**Primary Invariant:** A protocol-significant action without provenance is
incomplete.

```text
InferenceEvent {
  event_id
  previous_event_id
  actor
  subject
  provider
  capability
  action
  input_hash
  output_hash
  authorization_reference
  signature
}
```

The ledger MUST be append-only, reject mutation and deletion, and prevent
identifier reuse. A provenance record is authoritative only after acceptance
by a conforming ledger. Provider logs, application logs, analytics records,
and runtime traces are not provenance unless converted into accepted ledger
events.

---

## RFC-0008 — Session Lifecycle and Secure Cleanup

**Status:** Frozen  
**Primary Invariant:** Termination is a protocol state transition.

```text
CREATED -> AUTHORIZED -> ACTIVE -> TERMINATING -> CLEANED
                              |
                              -> CLEANUP_FAILED
```

Cleanup completion requires cleanup execution, successful verification, and
RFC-0007 provenance acceptance. A session MUST NOT transition to `CLEANED`
until cleanup is verified. UI termination, provider claims, transport closure,
and memory-release requests are insufficient proof of cleanup.

---

## RFC-0009 — Conformance and Interoperability

**Status:** Frozen  
**Primary Invariant:** Identical canonical inputs MUST produce identical
protocol outcomes.

This RFC defines test vectors, compliance levels, reference implementations,
and failure codes. RFC-0009 establishes execution truth: it proves what
happened under the protocol, rather than creating identity, authorization, or
artifact authority.

---

## RFC-0010 — Artifact Binding Authority

**Status:** Frozen  
**Primary Invariant:** Artifacts cannot create authority; they bind only to
already validated evidence.

```text
RFC-0009 execution truth -> RFC-0010 artifact provenance -> bound artifact
```

Artifact binding MUST NOT reconstruct, repair, substitute, synthesize
identity, or emit an artifact from a rejected state.

---

## RFC-0011 — Governance and Registry Authority

**Status:** Draft  
**Purpose:** Define protocol evolution without breaking compatibility.

This RFC defines the RFC, object, capability, error, and extension registries.
No new field, object kind, capability, error, or extension exists without
registration. Each registration MUST declare its purpose, classification, and
compatibility impact.

---

## RFC-0012 — Trust Federation and External Authority Bridges

**Status:** Draft  
**Purpose:** Define interoperability with external trust systems, including
enterprise PKI, government roots, hardware roots, and provider identity
systems.

```text
External root recognized != trusted != authorized
```

This RFC defines trust adapters, root stores, authority translation, and
quarantine rules. External recognition MUST NOT bypass internal validation,
identity binding, authorization, capability, or policy requirements.

---

## RFC-0013 — Sovereign Execution Boundary

**Status:** Draft  
**Purpose:** Define the complete execution authorization boundary.

An SIA execution is valid only when all of the following are present:

```text
Trusted input
+ canonical identity
+ authorized policy
+ declared capability
+ verified execution
+ recorded provenance
+ verified cleanup
+ bound artifact
= sovereign execution
```

RFC-0013 consumes, but does not weaken or replace, the authority decisions of
RFC-0001 through RFC-0012.

---

## Final Authority Separation

| RFC | Authority question |
| --- | --- |
| RFC-0001 | Can this object enter the system? |
| RFC-0002 | Who or what is it, and what grants apply? |
| RFC-0003 | What exact bytes represent it? |
| RFC-0004 | What capability may it use? |
| RFC-0005 | Who controls the identity binding? |
| RFC-0006 | Is this action allowed? |
| RFC-0007 | What happened? |
| RFC-0008 | Was execution securely terminated? |
| RFC-0009 | Does it conform? |
| RFC-0010 | Is the artifact bound to proof? |
| RFC-0011 | How does the protocol evolve? |
| RFC-0012 | How do external authorities connect? |
| RFC-0013 | Is the complete execution sovereign? |
