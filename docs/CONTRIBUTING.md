# Contributing to Sovereignty AI

## Before contributing

Read the [normative specification](SOVEREIGNTY_AI_SPECIFICATION_v1.0.md) and the relevant interface contracts before changing architecture or runtime behavior.

The specification is the authority. Supporting documents may clarify implementation but must not silently change normative requirements.

## Branching

Use focused branches for changes:

```text
feature/<short-description>
fix/<short-description>
docs/<short-description>
```

Do not make implementation changes directly on `main`. Keep architecture work isolated from unrelated application changes.

## Change control

A change that alters authority, identity, policy, data boundaries, startup order, runtime modes, evidence requirements, or a stable interface contract requires:

1. an update to the normative specification;
2. an Architecture Decision Record when the decision changes or constrains the architecture;
3. corresponding acceptance tests or an explicit test-plan update;
4. a changelog entry;
5. review before merge.

Additive, backward-compatible changes are preferred.

## Implementation rules

- Preserve the human owner as the only Root Authority.
- Treat AI participants as non-human, bounded participants.
- Keep the default decision `DENY`.
- Keep Offline as the default mode.
- Keep private data local by default.
- Do not initialize providers, network clients, polling loops, WebSockets, SSE streams, or credential consumers before `PolicyEngine` succeeds.
- Use `SCARLedger` as the canonical API name.
- Do not write credentials, session keys, or raw private payloads to evidence.
- Preserve safe cached dashboard behavior when live sources fail.
- Do not add mandatory cloud services or remote UI/CDN dependencies for local-first functionality.

## Documentation quality gate

Before merging documentation or architecture changes, verify:

- requirements are testable;
- interface sections include purpose, inputs, outputs, failure behavior, and audit requirements;
- `SCARLedger` naming is consistent;
- Root Authority wording is consistent;
- `NO ACTIVE MISSION` and `ACTIVE MISSION` terminology is used consistently;
- relative links resolve;
- no placeholder text remains;
- acceptance criteria are complete;
- informative examples are clearly labeled;
- Markdown renders correctly.

## Tests and validation

Run the repository's applicable formatter, linter, and test commands. For documentation-only changes, at minimum inspect the diff, validate links where tooling exists, and run:

```bash
git diff --check
git status --short
```

For runtime changes, add or update tests for the affected acceptance criteria. A failed protected operation must not be hidden by recovery logic.

## Security and privacy

Do not commit credentials, private keys, session tokens, raw prompts, vault contents, personal memory, or unapproved device data. Use redacted fixtures and references instead.

Report a suspected security issue privately to the repository owner rather than opening a public issue with sensitive details.

## Review standard

A reviewer must be able to determine:

- what authority was used;
- what data boundary applies;
- what policy decision occurs;
- what evidence is produced;
- how failure behaves;
- which acceptance criteria prove the change.
