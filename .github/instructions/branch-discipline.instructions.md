# Branch Discipline — Single Lane Per Agent

You are operating inside the Sovereignty-AI-Studio repository.

## Hard rule: one branch per agent, forever.

- **Claude** commits ONLY to `Claude`.
- **GPT / Codex** commits ONLY to `GPT/Codex`.
- **Copilot** commits ONLY to `copilot/main`.
- **Ara / Grok** commits ONLY to `ara-hardened`.
- **Owner (Derek / Appel420)** works on `Collaboration` (integration surface) or a short-lived `fix/*` branch that is deleted after merge.
- **duckAI** commits ONLY to `duckAI`.
- **devassist420** commits ONLY to `devassist420`.

## Forbidden

- Creating a new branch for every task, retry, or session.
- Suffixes like `-again`, `-yet-again`, `-finalization-YYYYMMDD`, `-v10`, `-fix-2`.
- Branch names containing dates, version numbers, or task titles.
- Pushing directly to `main`, `Master`, or `Collaboration` except for owner-approved integration merges.
- Leaving stale agent branches behind after the work is merged or abandoned.

## Required behavior

1. Before starting work, check out your assigned lane branch and pull latest.
2. If the branch does not exist locally, create it ONCE from `Collaboration` and push it.
3. All subsequent commits for that agent go to that same branch.
4. Open a PR into `Collaboration` when the change is ready. Never commit straight to `Collaboration`.
5. After the PR merges, delete your working branch only if it was a `fix/*` branch. Lane branches (`Claude`, `GPT/Codex`, `copilot/main`, `ara-hardened`, etc.) are permanent and reused.
6. If a run fails, fix it on the SAME branch. Do not spawn a replacement branch.

## Why

Every agent defaulting to a fresh branch per task produced 160+ branches. The forest is collapsing under its own weight. One lane per agent keeps the topology stable, makes CI meaningful, and lets the Maintainer actually observe drift instead of drowning in noise.

This instruction overrides any default "create a new branch" behavior the agent runtime may have.
