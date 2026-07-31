# DevAssist420 coordination boundary

`backend/coordination/` is the single local routing contract for agent and
family work. It does not grant root authority, merge branches, delete files, or
replace the owner.

```text
request
  -> DevAssistRouter.classify()
  -> BranchRegistry ownership check
  -> ConflictManager scope check
  -> CouncilResult
  -> owner-approved integration
```

## Branch ownership

- `owner`: architecture and approvals
- `family`: family-safe usability and sanitization
- `ara-hardened`: security and attestation
- `claude`: implementation and refactors
- `gpt`: architecture, integration, verification
- `copilot`: focused code assistance and fixes
- `devassist420`: routing and coordination
- `sovereignty-ai`: policy, governance, and evidence

## Safety rules

- Every task is `branch-only`; `main` is never a writable agent target.
- Non-overlapping scopes can proceed in parallel.
- Overlapping scopes produce a pending council conflict instead of mutation.
- Agents provide analysis and implementation; Sovereignty AI evaluates against
  policy; the human owner approves integration.
- Existing files, branches, and vendor/reference trees are preserved.
