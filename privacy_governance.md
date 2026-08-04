# Privacy Governance

## Status

- **Document:** `privacy_governance.md`
- **Status:** Governance specification
- **Implementation:** None authorized by this document alone
- **Target branch:** `copilot/main`
- **Promotion path:** Owner review → `collaboration` → validation → `main`

## Canonical principle

> Privacy is an attribute of people. Authority may be delegated to machines. Ownership of private information is never delegated to machines.

The Human-versus-Machine branch invariant is normative and locked.

## Branch classes

### Human branches — privacy sovereign

Human branches belong to natural persons and are privacy-protected by default.

#### Independent adult

```yaml
human_branch:
  class: independent_adult
  branch_root: self
  privacy: sovereign
  access:
    default: deny
  capability:
    required: true
    issuer: branch_root
    time_bounded: true
    signed: true
  data_ownership: branch_root
  audit:
    scar_required: true
```

Rules:

- The natural person is the root authority for their branch.
- Private content is denied by default, including to platform Root.
- Access requires an explicit, signed, time-bounded capability issued by the branch root.
- Platform administration does not transfer ownership of private content to Root.
- Protected deletion requires SCAR evidence and dual control or a defined recovery delay.
- Data ownership remains with the person.

#### Protected minor

A minor’s privacy remains protected, but lawful guardianship and age-based policy may provide a governed access path.

```yaml
human_branch:
  class: protected_minor
  branch_root: child
  privacy: protected
  guardian_policy:
    enabled: true
  access:
    default: deny
    permitted_via:
      - guardian_policy
      - court_order
      - child_capability_when_of_age
  audit:
    scar_required: true
```

Rules:

- The child remains the human branch root.
- Guardian access is not automatic; it must be authorized by the applicable guardian policy.
- Court orders and age-based transition rules may establish additional governed access.
- Every access decision must be auditable through SCAR.
- Protected deletion and retention remain subject to policy, evidence, and recovery safeguards.

## Machine branches — operational

Machine branches include GPT, Grok, Claude, Copilot, routers, CI systems, and other AI or automation contexts.

```yaml
machine_branch:
  class: operational
  authority: delegated
  privacy: operational
  auditable: true
  owner_inspection: allowed
  independent_rights: false
  memory: task_scoped_only
```

Rules:

- Machines are execution contexts, not persons.
- Machine branches do not own privacy-protected information.
- Machines receive only delegated, task-scoped authority and memory.
- Machine state is auditable by the human authority operating the system.
- Machine branches cannot become privacy-sovereign through naming, isolation, encryption, or branch placement.
- A branch name alone is not permission; registry state, policy, capability, and lease determine authority.

## Example branch tree

```text
Root (human)
 ├── Family
 │    ├── Wife Branch          ← human, independent adult, privacy sovereign
 │    └── Son Branch           ← human, protected minor, guardian/age policy
 ├── Grok Branch               ← machine, operational
 ├── GPT Branch                ← machine, operational
 ├── Claude Branch             ← machine, operational
 ├── Copilot Branch            ← machine, operational
 ├── Router Branch             ← machine, operational
 └── CI Branches               ← machine, operational
```

## Human-versus-Machine invariant

```text
Human branch
    ↓
Owns privacy

Machine branch
    ↓
Executes delegated authority
```

Machines can receive capabilities, but they never become sovereign owners of information. They operate under delegated authority and remain subject to policy, audit, and human governance.

## Governance boundaries

```text
Human ownership
  → capability and policy
  → lease and scope validation
  → machine execution context
  → QuadRatchet data protection
  → SCAR governance evidence
  → owner-controlled review and promotion
```

The following concerns remain separate:

| Layer | Responsibility |
|---|---|
| Human branch | Owns privacy and private information |
| Policy | Defines permitted access and use |
| Capability | Delegates bounded authority |
| Lease | Limits current scope and duration |
| Machine branch | Performs delegated operations |
| QuadRatchet | Protects generated or stored data |
| SCAR | Records governed events and evidence |
| Branch registry | Records branch identity and write authority |
| Owner review | Controls collaboration and promotion |

## Protected access and deletion

For independent adult branches:

```text
no capability
  → access denied

valid signed capability
  → policy and lease validation
  → bounded access
  → SCAR evidence
```

For protected minor branches, guardian or court-authorized paths must still be policy-controlled, time-bounded where applicable, and auditable.

Deletion of protected content requires:

- an authenticated governing request;
- applicable capability or guardian-policy authorization;
- policy and lease validation;
- SCAR event recording;
- dual control, recovery delay, or equivalent protection where required.

## Implementation boundary

This document freezes the governance rule. It does not authorize runtime behavior, repository mutation, deployment, or access to private content by itself.

```text
specification
  → implementation proposal
  → isolated validation
  → evidence
  → owner review
  → collaboration integration
  → validation
  → main promotion
```

The document is placed on `copilot/main` for review. No changes to `collaboration` or `main` are included.
