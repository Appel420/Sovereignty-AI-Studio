# SuperGrok Heavy 4.2 Integration

This document defines how `Sovereignty-One/SuperGrok-Heavy-4-2-Skeleton` coincides with `Appel420/Sovereignty-AI-Studio` without allowing unreviewed changes into `main`.

## Source repository

- Source: `Sovereignty-One/SuperGrok-Heavy-4-2-Skeleton`
- Clone URL: `https://github.com/Sovereignty-One/SuperGrok-Heavy-4-2-Skeleton.git`
- Default branch: `main`
- Studio mount path: `vendor/supergrok-heavy-4-2-skeleton`
- Owner agent: Ara / Grok

## Symmetry model

Each AI agent has a dedicated branch and must work through pull requests:

| Agent | Provider | Branch | Function |
| --- | --- | --- | --- |
| Ara | xAI Grok | `ara-hardened` | Hardened security workspace and SuperGrok ownership |
| Claude | Anthropic | `claude` | Development workspace |
| GPT / Codex | OpenAI | `gpt` | Architecture, integration, verification |
| Copilot | GitHub | `copilot` | Code assistance workspace |

## Import strategy

Use one of two approved strategies:

1. **Vendor copy**: copy the source repository into `vendor/supergrok-heavy-4-2-skeleton` while excluding `.git`.
2. **Git subtree**: import the source repository as a subtree so updates can be pulled later.

Submodule mode is intentionally avoided unless all runtime environments can initialize submodules reliably.

## Required invariants

- `main` remains protected.
- Agent branches do not push directly to `main`.
- Changes enter `main` through reviewed pull requests.
- SuperGrok/Ara changes originate from `ara-hardened` or a dedicated integration branch.
- `agent-workspaces.json` remains the source of truth for branch-to-agent mapping.

## Local subtree import command

From the root of `Sovereignty-AI-Studio`:

```bash
git checkout main
git pull

git checkout -b integrate/supergrok-heavy

git remote add supergrok-heavy https://github.com/Sovereignty-One/SuperGrok-Heavy-4-2-Skeleton.git || true
git fetch supergrok-heavy main

git subtree add --prefix=vendor/supergrok-heavy-4-2-skeleton supergrok-heavy main --squash

git add agent-workspaces.json docs/supergrok-heavy-integration.md scripts/sync-supergrok-heavy.sh
git commit -m "Integrate SuperGrok Heavy workspace"
git push -u origin integrate/supergrok-heavy
```

## Local vendor-copy import command

Use this if subtree is unavailable:

```bash
git checkout main
git pull

git checkout -b integrate/supergrok-heavy
mkdir -p vendor
rm -rf /tmp/supergrok-heavy-4-2-skeleton vendor/supergrok-heavy-4-2-skeleton

git clone https://github.com/Sovereignty-One/SuperGrok-Heavy-4-2-Skeleton.git /tmp/supergrok-heavy-4-2-skeleton
rm -rf /tmp/supergrok-heavy-4-2-skeleton/.git
cp -R /tmp/supergrok-heavy-4-2-skeleton vendor/supergrok-heavy-4-2-skeleton

git add vendor/supergrok-heavy-4-2-skeleton agent-workspaces.json docs/supergrok-heavy-integration.md scripts/sync-supergrok-heavy.sh
git commit -m "Vendor SuperGrok Heavy into Studio"
git push -u origin integrate/supergrok-heavy
```

## Sync update command

After the first import, run:

```bash
./scripts/sync-supergrok-heavy.sh
```
