# Branch Reference Audit

## Finding

The repository's current default branch is `Collaboration`. GitHub still contains both `Collaboration` and `collaboration`, plus legacy `Main` and `Master` refs. The application branch registry also treats lowercase `main`, `master`, and `collaboration` as protected names, but does not model the actual canonical repository branch `Collaboration`.

## Confirmed blockers

1. Repository default branch is `Collaboration`.
2. The CI workflow on `Collaboration` contains `runs-on: self-hosted linux ARM64`, which is an invalid/ambiguous runner selector for the intended three-label form.
3. Existing repository evidence shows scripts and upload paths assuming `main`; this is the direct cause of errors such as `Branch main not found` when operating against this repository.
4. The branch registry protects lowercase `main`, `master`, and `collaboration`, but omits canonical `Collaboration`, creating a governance mismatch.
5. `verify_ci_policy.py` permits `push` and `pull_request` triggers even though the current governance record says automatic execution is frozen and `workflow_dispatch` is the intended explicit trigger.

## Repair boundary

This audit does not rename or delete branches, does not alter `Main`/`Master`, and does not promote anything into production. The canonical repository integration branch remains `Collaboration` until the owner explicitly changes it.

## Required follow-up

- Make branch-aware tooling resolve the repository's actual canonical integration branch instead of hardcoding `main`.
- Add `Collaboration` to protected branch governance where it is the repository's canonical integration branch.
- Normalize CI runner selectors to an explicit supported form after deciding between genuine self-hosted ARM64 and hosted ARM64 execution.
- Align CI trigger validation with the frozen workflow policy.
