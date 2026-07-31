# Owner agent guidelines (all agents)

**Same rules for every agent.** Ara, Claude, GPT, Copilot, DevAssist420, and any other helper follow this document equally.

## Core rule

**Read and understand the project before starting any implementation.**

No agent begins coding from assumptions. No agent skips discovery because it “already knows.” The repository and the owner’s current request are the source of truth.

## Required order of work

1. **Read** — open the real files that matter for the task.
2. **Understand** — what exists, what is broken, what the owner asked.
3. **State** — short summary of findings (paths + facts).
4. **Implement** — minimal diff only.
5. **Verify** — local check when available; no false “fixed.”

Skipping step 1–3 is non-compliance.

## Shared rules

1. **Read first** — always.
2. **One lane** — assigned branch only; never another agent’s branch; never push `main` or `collaboration`.
3. **Runner** — only `runs-on: ['self-hosted Linux arm64']` in first-party workflows.
4. **Local/offline** — no cloud agent path by default.
5. **Delete nothing** without explicit owner order.
6. **Fail closed** — if blocked, report `BLOCKED` with file and reason.

## Branch topology

| Branch | Role |
|--------|------|
| `main` | Production — owner-controlled |
| `collaboration` | Integration/reconciliation — owner-controlled |
| Agent lanes (`ara-hardened`, `claude`, `gpt`, `copilot`, `copilot/main`, `devassist420`, …) | Development only |

### Owner-controlled operations (`main`, `collaboration`)

Authorization stays with the owner. Physical actor may be:

- owner-approved merge
- owner-approved cherry-pick
- **owner-authorized integration daemon**

Agents do not commit to `collaboration` or `main`. A daemon may promote only when the owner has explicitly authorized that service; the daemon does not become an agent workspace.

Required evidence for accepted integration inputs:

- SCAR evidence reference
- lease reference (when leases are in use)
- registry version
- verification results
- conflict record when applicable

## Sources of truth

| File | Role |
|------|------|
| `config/owner-execution-policy.json` | Machine policy |
| `config/branch-registry-policy.json` | Branch roles + accepted operations |
| `.github/copilot-instructions.md` | Binding agent instructions (all agents) |
| `docs/OWNER_AGENT_GUIDELINES.md` | This document |

## Owner promotion

Agent branch → owner review → `collaboration` (optional integration) → `main`. Agents do not merge to `collaboration` or `main`.
