# Local-First Repository Governance

**Status:** LOCKED
**Owner authority:** Human entity owner only
**Scope:** Copilot sessions, repository work, local CI, cloud-agent use, branch synchronization, and promotion to `main`.

## Rule 1 — Offline/local first

All work MUST begin in offline/local mode whenever the required files, tools, and repository state are available locally.

The standard development path is the repository-owned local CI, including:

- `scripts/local-ci.sh`
- `scripts/v1_local-ci.sh`
- other explicitly selected local validation scripts

Local CI MUST NOT invoke GitHub Actions, hosted runners, cloud agents, publishing, provider calls, or external OAuth services.

## Rule 2 — Cloud use requires announcement and consent

If cloud execution, a hosted runner, a cloud agent, remote provider, external OAuth service, or any other external execution path is being considered or used, the assistant MUST:

1. Announce that cloud/external execution is being considered or required.
2. State exactly what would be sent or executed externally.
3. Identify the destination and purpose.
4. Wait for explicit consent from the human entity owner.

Cloud or external execution MUST NOT be used without that consent. Silence, login, repository access, or a prior approval for another action does not constitute consent.

## Rule 3 — Branches are the working boundary

Work MUST be performed on the assigned dedicated branch. Existing dedicated branches MUST be reused when appropriate; a new branch MUST NOT be created merely because a task is continuing.

The assistant MAY pull, fetch, rebase, or otherwise update its branch from `main` when needed and when the operation remains within the approved local/offline boundary.

## Rule 4 — No push or promotion to `main` without owner consent

The assistant MUST NOT push commits to `main`, merge into `main`, enable automatic promotion to `main`, or otherwise promote branch contents to `main` without explicit consent from the human entity owner for that specific promotion.

Pulling updates from `main` into a working branch is permitted. Pushing from a working branch to `main` is prohibited until the human entity owner explicitly authorizes it.

## Required status announcement

Before work begins, the assistant must state one of:

```text
MODE: LOCAL/OFFLINE
CLOUD: NOT USED
BRANCH: <working branch>
MAIN PUSH: PROHIBITED WITHOUT HUMAN OWNER CONSENT
```

or, only after explicit consent:

```text
MODE: EXTERNAL/CLOUD — OWNER CONSENT RECORDED
DESTINATION: <named destination>
DATA/ACTION: <exact scope>
BRANCH: <working branch>
MAIN PUSH: PROHIBITED WITHOUT SEPARATE HUMAN OWNER CONSENT
```

## Non-negotiable invariants

```text
OFFLINE FIRST
CLOUD MUST BE ANNOUNCED
CLOUD REQUIRES HUMAN OWNER CONSENT
PULLING FROM MAIN IS ALLOWED
PUSHING TO MAIN REQUIRES HUMAN OWNER CONSENT
ASSISTANT != OWNER AUTHORITY
```
