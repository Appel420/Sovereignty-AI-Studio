# SGHV119 Consolidation Plan

## Problem

`SGHV119.html` is becoming a catch-all file. That makes the system harder to audit, harder to run on iPhone, and harder to secure.

The correct fix is not another giant dashboard. The correct fix is a small static control surface with a strict helper spine.

## Target Shape

```text
SGHV119.html
  -> helpers/command-bus.js
  -> helpers/bridge-adapter.js
  -> helpers/voice-adapter.js
  -> helpers/terminal-adapter.js
  -> helpers/agent-adapter.js
  -> helpers/fixer-adapter.js
  -> crypto/pqc-provider.js
```

## Rules

1. `SGHV119.html` stays small.
2. No React.
3. No browser `ws://` control channel.
4. No vendor key-generation API.
5. No fake PQC fallback.
6. No direct calls to dirty providers from the UI.
7. Every helper has one job.
8. Every helper talks through the command bus.
9. All agent work maps to GitHub branches.
10. If PQC provider is unavailable, crypto must fail closed.

## Communication Spine

All user interactions become commands:

```json
{
  "type": "agent.task",
  "target": "gpt",
  "branch": "gpt",
  "payload": {
    "message": "fix this bug"
  }
}
```

The command bus routes the command to the correct helper.

## Helper Responsibilities

| Helper | Purpose |
| --- | --- |
| `command-bus.js` | Central event router. No network logic. |
| `bridge-adapter.js` | HTTPS calls to Node bridge. |
| `voice-adapter.js` | iPhone/Safari speech input/output where available. |
| `terminal-adapter.js` | Terminal command request interface. No raw shell by default. |
| `agent-adapter.js` | Ara/Grok, Claude, GPT, Copilot routing. |
| `fixer-adapter.js` | Fixers, bug hunters, validators, council tasks. |
| `pqc-provider.js` | Local/native PQC key interface. Fails closed if missing. |

## Agent Branch Map

| Agent | Branch |
| --- | --- |
| Ara / Grok | `ara-hardened` |
| Claude | `claude` |
| GPT / Codex | `gpt` |
| GitHub Copilot | `copilot` |

## Shrink Plan

1. Freeze `SGHV119.html` as a shell only.
2. Move inline JavaScript into helpers.
3. Remove React frontend from active runtime.
4. Replace socket assumptions with HTTPS command calls.
5. Add PQC provider boundary.
6. Connect helpers through the command bus.
7. Delete duplicate dashboards after verified migration.

## Definition of Done

`SGHV119.html` should only contain:

- Layout
- Mobile UI controls
- Script imports
- No business logic
- No provider-specific code
- No hardcoded external model APIs
- No key generation claims unless the PQC provider is active
