## Ara — Sovereign Maintainer Agent

**Ara** is a custom GitHub Copilot agent that acts as a collaborative council between Grok, Claude, and Codex.

It aggressively maintains codebase health with strong focus on **persistent memory (REPMHL)**, token/session rotation resilience, and long-term architectural quality.

### How to Enable

1. Place the agent config at `.github/agents/ara-sovereign-maintainer.md`
2. Reference it in Copilot Chat: `@ara-sovereign-maintainer ...`

### Key Strengths
- Direct file edits + clean PRs (no Actions dependency)
- Strict hydration validation after memory/state refactors
- Rotation handoff enforcement
- Multi-backend support (software, Secure Enclave, hybrid)

### Example Commands

```bash
@ara-sovereign-maintainer Refactor REPMHL with proper hydration validation test cases.
@ara-sovereign-maintainer Add clean token rotation handoff logic.
@ara-sovereign-maintainer Reorganize sovereign/ directory and fix imports.
```