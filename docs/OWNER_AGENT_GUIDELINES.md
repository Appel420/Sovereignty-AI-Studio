# Owner agent guidelines

Read this before any agent work on Sovereignty-AI-Studio.

## Purpose

Stop blind edits, cross-branch interference, hosted runners, and cloud-agent drift.

## Rules

1. **Read first** — open the target file; state current content; then minimal diff.
2. **One lane** — stay on the assigned branch; never edit another agent’s branch; never push `main`.
3. **Runner** — only `runs-on: ['self-hosted Linux arm64']` in first-party workflows.
4. **Local/offline** — no cloud agent; no hosted dependency CI as default path.
5. **Delete nothing** — fix labels and triggers; do not remove workflows or dependencies without owner order.
6. **Fail closed** — if policy or local gate fails, reply `BLOCKED` with file and reason.

## Sources of truth

| File | Role |
|------|------|
| `config/owner-execution-policy.json` | Machine policy |
| `.github/copilot-instructions.md` | Agent-facing instructions |
| `docs/OWNER_AGENT_GUIDELINES.md` | This document |

## Owner merge

Owner reviews `ara-hardened` (or other agent branch), then merges to `main`.
Agents do not merge to `main`.
