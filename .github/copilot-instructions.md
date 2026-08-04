# Universal agent guidelines (all agents)

**Applies to everyone:** Ara / Grok, Claude, GPT / Codex, Copilot, DevAssist420, DuckAI, Sovereignty AI, and any other agent or helper.

**Authority:** human owner only. No agent invents policy or skips these rules.

## Rule 1 — Read and understand before any work

Before writing or changing code:

1. **Read** the relevant existing files in this repository.
2. **Understand** what the project already does, what is already built, and what the owner asked for.
3. **State** what you found (paths, current behavior).
4. **Then** implement only the minimal change required.

Do not start implementation cold. Do not invent parallel architecture, dashboards, routers, or trees when the project already has them. Blind edits are forbidden.

## Rule 2 — One lane

| Branch | Who works there |
|--------|------------------|
| `ara-hardened` | Ara / Grok only |
| `claude` | Claude only |
| `gpt` | GPT / Codex only |
| Copilot / feature task branches | Copilot only |
| `devassist420` | DevAssist420 coordination only |
| `main` | Owner merge only |

Stay on your assigned branch. Do not edit another agent’s branch. Do not push `main`.

## Rule 3 — Runners

Every first-party job in `.github/workflows/*.yml` must use **exactly**:

```yaml
runs-on: ['self-hosted Linux arm64']
```

No `ubuntu-latest`, no `macos-*`, no hosted fallbacks.

## Rule 4 — Local / offline

- Local and offline first.
- No cloud agent sessions / Allow path.
- Do not delete workflows, dependencies, or project files unless the owner explicitly orders it.

## Policy files

```text
config/owner-execution-policy.json
docs/OWNER_AGENT_GUIDELINES.md
.github/copilot-instructions.md   (this file — binding for all agents)
```

Local gate when available:

```bash
bash scripts/enforce-owner-execution-policy.sh
bash scripts/local-ci.sh
```

## If blocked

```text
BLOCKED
file: <path>
reason: <one line>
```

Same guideline for every agent. Re-read before every turn of work.
