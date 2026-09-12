# Agent Lanes

Agent lanes are development and review boundaries, not authority domains.

| Lane | Role | Canonical output | Branch |
| --- | --- | --- | --- |
| Copilot | Implementation and CI changes | Commits, patches, tests | `copilot/main` |
| Claude | Review and implementation lane | Reviews, focused commits | `claude` |
| Grok/Ara | Security and architecture review | Findings and security evidence | `ara-hardened` |
| DevAssist420 | Coordination and execution support | Coordination records | `DevAssist420` |
| DuckAI | Independent analysis | Review records | `DDG/DuckAI-main` |
| OpenAI/ChatGPT/Codex | Implementation and review | Commits, patches, tests | `GPT/Codex` |
| xAI/Grok | Receipts, 5W1H ledger, gate enforcement | Signed events, SCAR appends | `xAI/Grok` |

## Rules

1. Do not place canonical runtime code in agent or email folders.
2. Treat conversation text as a reasoning trail until committed to a repository contract.
3. Keep one focused capability per change stream.
4. Record irreversible decisions in `docs/DECISIONS.md`.
5. Use `CURRENT_STATE.md` to prevent context loss.
6. Promotion remains owner-controlled.
7. Persistent lane branches only. No per-task `fix/*` or `patch-*` branches. Fix in place on the lane branch.
8. Sync to Collaboration tip before starting work on a lane.

Recommended interaction-record layout outside canonical runtime code:

```text
.ai/
├── OpenAI/
│   ├── decisions/
│   └── reviews/
├── Claude/
│   └── reviews/
├── Copilot/
│   └── patches/
├── Grok-Ara/
│   └── security/
├── xAI/
│   └── receipts/
└── DevAssist420/
    └── execution/
```
