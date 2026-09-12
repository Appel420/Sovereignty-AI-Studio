# Agent Lane Contract

This repository uses dedicated agent/vendor lanes. A lane is a persistent branch, not a disposable task branch.

## ChatGPT / Codex lane

- Dedicated branch: `GPT/Codex`
- Repository base branch: `Collaboration`
- All ChatGPT/Codex implementation work starts on `GPT/Codex`.
- Before any work, synchronize `GPT/Codex` with the current `Collaboration` tip.
- Do not create task-specific branches such as `GPT/Codex-fix-*`.
- Keep all fixes for the same workstream on `GPT/Codex`.
- Open the pull request from `GPT/Codex` to `Collaboration`.
- If validation fails, fix the failure on `GPT/Codex`, push the new commit, and let the existing PR update.
- Do not create a second PR or a second branch merely because CI failed.
- Do not merge stale work based on an outdated `Collaboration` snapshot.

## General lane rule

Each AI/company integration that has a dedicated lane must remain in that lane. The lane identifies ownership and provides a stable audit boundary. Task descriptions belong in commits and PRs; they do not become new branch names.

## Required workflow

`Collaboration` current tip -> synchronize dedicated lane -> implement -> push -> PR to `Collaboration` -> validate -> fix on the same lane if needed -> merge only when gates pass.
