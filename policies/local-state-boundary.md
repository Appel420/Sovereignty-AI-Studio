# Local-State Boundary

This contract remains inside `Sovereignty-AI-Studio` until the Human Owner explicitly approves a separate repository. It is the canonical description of device-local registry metadata, not a copy of private memory.

## Authority

The Human Owner is the only authority. Provider names, folder names, branch names, credentials, or tool availability do not grant permission.

## Privacy

Only schemas, public-safe examples, policies, and tests may be committed. Real device state remains under the device-local state root and is never committed.

## Execution

- Network is disabled by default.
- External memory is disabled by default.
- Remote listening is disabled.
- Wake-word recognition is `local_engine_required` and `not_configured` unless separately verified on the device.
- Missing local state produces `UNAVAILABLE` or `DENY`; it never triggers cloud substitution.
- The dashboard is read-only with respect to the registry.

## Key boundary

No startup, dashboard load, test, CI step, or migration script may generate, rotate, or replace keys. Missing key material is an explicit unavailable state. Key files and credentials are excluded from this repository.

## Voice boundary

Dictated text is provisional. Low-confidence speech, homophones, repository names, branch names, protected actions, and local-first conflicts require read-back confirmation. Confirmation of transcription is not authorization to execute.

## Repository boundary

Do not create a second repository or disposable branch for this contract during migration. Keep the work on `feature/canonical-governance-core` until the Human Owner approves a permanent repository decision.
