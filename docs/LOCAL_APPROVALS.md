# Local approval notifications

The local runtime must notify the owner before a governed operation proceeds.
Notifications are device-local records; they are not permissions by themselves.

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
    -> OWNER APPROVED or OWNER DENIED
    -> OPERATION MAY PROCEED or MUST BE BLOCKED
```

An approval record does not execute the operation. The caller must separately enforce the decision. This prevents the notification layer from becoming an authority or hidden execution path.

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
