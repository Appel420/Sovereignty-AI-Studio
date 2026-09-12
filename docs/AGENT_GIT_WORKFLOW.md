# Agent Git Workflow Rules (Mandatory)

**Status:** ENFORCED for all agent sessions (Grok, Ara, Claude, Codex, Copilot, DuckAI).
**Owner:** Appel420 / Derek Appel
**Agreement:** Grok_Edu v2.0 Development & Compliance Agreement, February 21, 2026

## Core Rule

No agent may write directly to `main`, `Collaboration`, or any protected/default branch.

Every change follows this exact path:

1. **Create a dedicated branch** from the current base (`Collaboration` unless specified).
   - Naming: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`, `security/<short-name>`.
2. **Commit all changes on that branch only.**
3. **Open a Pull Request** targeting `Collaboration` (or the specified base).
4. **Do not merge.** Dual sign-off required for major permanent changes (90-day rotating co-signer).
5. **Do not push secrets, credentials, private keys, or private state.**

## Forbidden Actions

- Direct commit/push to `main` or `Collaboration`.
- Using `push_files` or `create_or_update_file` against a protected branch.
- Skipping the branch step "because it's small."
- Committing `.env`, `credentials.env`, private keys, or Tuta passwords.

## Required Before Any Write

- Confirm base branch.
- Create branch.
- Verify branch exists (`list_branches`).
- Write files to the branch.
- Create PR.
- Report PR URL + branch name.

## Tuta / Email Connectors

- Only local, E2E, on-device connectors are permitted (tutamcp + tutaproxy).
- No Gmail, Outlook, or third-party cloud email accounts may be connected to the vault.
- All Tuta credentials stay in a `chmod 600` host file, never in git.

## Verification

After creating a PR, the agent must:

- List open PRs and confirm the new one appears.
- Confirm no direct writes to protected branches occurred in the same session.

Violation of this rule is a **Red Alert** event.
