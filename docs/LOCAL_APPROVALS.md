# Local approval notifications

The local runtime must notify the owner before a governed operation proceeds.
Notifications are device-local records; they are not permissions by themselves.

## Hybrid owner-control rule

**A policy block applies to the requested operation, never to the human owner.**

The system may deny, quarantine, or hold an operation, destination, provider, model, plugin, or network path. It MUST NOT use that decision to lock the owner out of the device, the local control plane, local evidence, configuration inspection, or the ability to make a subsequent owner decision.

The owner must retain a device-local control path that does not depend on the blocked destination, provider, network, cloud service, model, watcher, fixer, or external notification service.

The owner decision model is explicitly hybrid:

```text
OBSERVED / BLOCKED REQUEST
        |
        +----> OWNER INSPECTS WHAT HAPPENED
        |             |
        |             +---- ACCEPT -> explicit authorization path
        |             |
        |             +---- DENY   -> operation remains blocked
        |             |
        |             +---- HOLD   -> remain pending for later decision
        |
        +----> NO OWNER DECISION -> MUST NOT silently execute
```

An **ACCEPT** decision authorizes only the exact requested scope represented by the approval/capability. It does not permanently allow the destination, provider, domain, model, plugin, or future operations. A **DENY** blocks that requested operation without disabling owner access.

A blocked domain is therefore observable and reviewable. Blocking means **the target operation cannot proceed under the current policy**; it does not mean the owner cannot inspect the request, read local evidence, change policy through the authorized local control path, or explicitly approve a permitted exception.

## Owner access invariant

The following is normative:

```text
OWNER ACCESS = ALWAYS AVAILABLE LOCALLY

BLOCK TARGET ACTION
        !=
BLOCK HUMAN OWNER
```

No automated component may:

- disable the owner's local control interface;
- revoke the owner's ability to inspect evidence;
- prevent the owner from accepting or denying a pending request;
- make the owner dependent on the blocked network path to regain control;
- turn a denied operation into an owner lockout;
- treat a domain block as a device-wide access block.

If the normal control path is degraded, an owner-local recovery path must remain available. If canonical authorization state cannot be verified, the affected privileged action fails closed, while owner access to local recovery, diagnostics, and evidence remains available.

## Governed operation kinds

```text
PROCESS
    starting, stopping, restarting, or enabling a local service

DEPLOYMENT
    promoting or deploying an artifact, build, or runtime configuration

COMMIT
    creating, signing, merging, or pushing a repository commit
```

Each request is stored in `state/approvals.jsonl` and includes:

- approval kind and subject;
- summary and requested-by identity;
- exact payload or artifact metadata;
- creation and notification timestamps;
- notification count;
- pending/approved/denied/expired/cancelled state;
- owner decision and audit evidence.

Repeated pending requests are deduplicated and only increment their notification count.

## Required decision flow

```text
OPERATION PROPOSED
    -> LOCAL NOTIFICATION
    -> OWNER INSPECTS REQUEST
    -> OWNER APPROVED / DENIED / HELD
    -> EXACT AUTHORIZATION CHECK
    -> OPERATION MAY PROCEED or MUST BE BLOCKED
```

An approval record does not execute the operation. The caller must separately enforce the decision. This prevents the notification layer from becoming an authority or hidden execution path.

Approval is not permanent authority. Where the operation is state-changing or otherwise capability-gated, the approval must feed the established authority/capability path and the execution must remain separately evidenced.

## Blocked-domain behavior

A domain or provider block should be treated as a **policy observation and enforcement event**, not as an invisible wall around the owner.

The local control plane should expose at minimum:

- requested destination/domain;
- requesting component;
- requested operation;
- current policy decision;
- reason for the block;
- timestamp;
- evidence/receipt reference when available;
- owner decision controls.

The system must not claim that a blocked request never occurred. The event remains owner-visible.

If the owner explicitly accepts an exception, the resulting authorization must be narrow, auditable, time-bounded where appropriate, and tied to the exact requested operation. The exception must not silently rewrite the global blocklist.

## CLI

```bash
python3 scripts/local_approvals.py request COMMIT abc123 "Commit runtime fix" --requested-by local-agent
python3 scripts/local_approvals.py list --state PENDING
python3 scripts/local_approvals.py decide <approval-id> APPROVED --owner Appel420
```

No process launcher, deployment target, GitHub API, cloud agent, or third-party notification service is invoked by this module.

## Verification

```bash
python3 -m pytest tests/test_approvals.py tests/test_issue_suggestions.py -q
```
