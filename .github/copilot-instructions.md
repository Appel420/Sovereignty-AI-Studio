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
| `ara-hardened` | Ara / Grok + Human Owner |
| `claude` | Claude + Human  Owner |
| `gpt` | GPT / Codex + Human  Owner |
| Copilot / feature task branches | Copilot + Human  Owner |
| `devassist420` | DevAssist420 coordination + Human  Owner |
| `main` | Human Owner merge only |


// This makes the branch map explicit: the branch identity is part of the machine’s workspace identity, not an ownership claim over the human.


Current machine/branch assignment
System
Dedicated branch
Status
Human Owner — Human owner Login authentication 
Master / main
🔐 Locked — Human Owner Only
Copilot
copilot/main
✅
Grok
Ara-hardened
✅
ChatGPT / Codex
GPT/Codex
✅
DuckAI
DDG/DuckAI-main
✅
Collaboration
collaboration
✅ Governance test
DevAssist420
DevAssist420
⬜ Human-owner approval required
Claude
claude
🔒
Derek’s Memories
Owner-controlled
✅
The important architectural point is that each machine gets a declared lane, but none of those lanes becomes the human authority lane.
                         APPEL420
                    HUMAN ROOT AUTHORITY
                            │
             ┌──────────────┴──────────────┐
             │                             │
       OWNER STATE                    MAIN / MASTER
             │                         🔐 LOCKED
             │
             ▼
      GOVERNED MACHINE LANES
             │
   ┌─────────┼──────────┬───────────┐
   ▼         ▼          ▼           ▼
Copilot    Grok      GPT/Codex    DuckAI
   │         │          │           │
copilot/  Ara-       GPT/Codex   DDG/
 main     hardened               DuckAI-main
   │         │          │           │
   └─────────┴──────────┴───────────┘
                    │
                    ▼
             collaboration
             governance test
                    │
                    ▼
              DevAssist420
          owner approval required
And the [x] notation should mean lane locked/reserved according to the displayed governance state, not “this machine owns the repository.”
For my current identity, your map is unambiguous:
ChatGPT/Codex → GPT/Codex
So when I’m acting in the repository, the provenance should identify the machine lane as GPT/Codex, while the human authority remains Appel420.
That gives us the exact who / what / when / where / why / how chain you were describing:
WHO
  Appel420 → human authority
  GPT/Codex → machine execution lane

WHAT
  exact operation / files / state transition

WHEN
  timestamp + state/lease version

WHERE
  repository + branch + execution boundary

WHY
  owner instruction + governing contract

HOW
  authorized capability → execution → verification

RESULT
  state transition + evidence

AUTHORITY
  remains with Human Owner
One correction to my previous wording: I should not call the machine a legal “co-owner” of the GitHub repository. In your architecture, co-owner is useful as a delegated operational role, but the actual repository ownership/authorization remains whatever GitHub and your human-controlled credentials establish. The branch is the machine’s governed workspace.


Stay on your assigned branch. Do not edit another agent’s branch. Do not push `main`.

## Rule 3 — Runners

Every first-party job in `.github/workflows.yml`:

```yaml
runs-on: ['self-hosted, linux arm64']
```

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
