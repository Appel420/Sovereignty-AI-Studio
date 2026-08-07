# Agent Lanes

Agent lanes are development and review boundaries, not authority domains.

| Lane | Role | Canonical output |
| --- | --- | --- |
| Copilot | Implementation and CI changes | Commits, patches, tests |
| Claude | Review and implementation lane | Reviews, focused commits |
| Grok/Ara | Security and architecture review | Findings and security evidence |
| DevAssist420 | Coordination and execution support | Coordination records |
| DuckAI | Independent analysis | Review records |
| OpenAI/ChatGPT/Codex | Implementation and review | Commits, patches, tests |

## Rules

1. Do not place canonical runtime code in agent or email folders.
2. Treat conversation text as a reasoning trail until committed to a repository contract.
3. Keep one focused capability per change stream.
4. Record irreversible decisions in `docs/DECISIONS.md`.
5. Use `CURRENT_STATE.md` to prevent context loss.
6. Promotion remains owner-controlled.

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
└── DevAssist420/
    └── execution/
```
