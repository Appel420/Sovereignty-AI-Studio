# Owner agent guidelines (read first)

**Authority:** human owner only. Agents do not invent policy.

## Read first

Before any edit:

1. Read the exact target file(s).
2. State what is there now.
3. Propose a minimal diff.
4. Do not invent architecture, dashboards, or trees that already exist.

Blind edits are forbidden.

## Lanes

| Branch | Owner |
|--------|--------|
| `ara-hardened` | Ara / Grok only |
| `claude` | Claude only |
| `gpt` | GPT / Codex only |
| Copilot task / feature branches | Copilot only |
| `main` | Owner merge only |

- Do not touch another agent’s branch.
- Do not push `main`.

## Runners

Every first-party job in `.github/workflows/*.yml` must use **exactly**:

```yaml
runs-on: ['self-hosted Linux arm64']
```

Forbidden:

- `ubuntu-latest`
- `macos-latest` / `macos-15`
- malformed or mixed runner labels
- GitHub-hosted fallbacks

## Local / offline

- Local and offline first.
- No cloud agent sessions.
- No “Confirm cloud agent” / Allow path.
- Do not delete workflows, dependencies, or project files (`delete_nothing`).

## Policy source

Machine-readable policy:

```text
config/owner-execution-policy.json
```

Local gate (when present on the machine):

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

Do not claim fixed without local evidence. Re-read this file every turn before acting.
