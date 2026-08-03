# Copilot Memory

## Scope
- Repository: `Appel420/Sovereignty-AI-Studio`
- Branch: `copilot/main`
- This branch is Copilot's dedicated work and memory lane.
- Do not write Copilot work directly to `main` or `collaboration`.

## Repository boundaries
- `Sovereignty-AI-Studio` is the application surface, local policy, coordination contracts, memory, evidence, and dashboard repository.
- `DevAssist420` is a separate local operator/runtime repository.
- `Sovereignty-AI-Gate` is a separate authority source when explicitly connected; do not merge these repositories or silently substitute one for another.

## Current integration model
```text
Sovereignty-AI-Studio authority/policy
  -> RouteDecision
  -> DevAssist420 local execution
  -> ExecutionReceipt
  -> SCAR/evidence
```

- The gate authorizes; DevAssist executes only an approved local route.
- External writes and cloud fallback remain disabled unless explicitly authorized.
- Device-local state is authoritative.
- Owner access must remain available and must not be silently hidden or blocked.

## Memory implementation
- `FixLoopingAiAndSaveMemory.py` belongs to `Sovereignty-AI-Studio`.
- It uses the repository's `memory/store.py` and `memory/hydration.py` SQLite-backed memory path.
- Before changing it, preserve local-only routing, persistence, loop detection, and owner visibility.
- Do not redirect this work to `DevAssist420` unless the owner explicitly requests a cross-repository integration change.

## Working rules
1. Read the target repository and branch first.
2. Make the smallest focused change.
3. Save durable Copilot notes here on `copilot/main`.
4. Record exact paths, decisions, tests, and blockers.
5. Never claim a test or implementation was completed unless verified.

## Latest owner direction
- Use the existing dedicated Copilot branch.
- Save Copilot memories on this branch.
- Stop expanding the architecture when a focused implementation is requested.
- Keep the owner in control and do not create an owner lockout through hardening.

## Next concrete work
- Stabilize `FixLoopingAiAndSaveMemory.py` in `Sovereignty-AI-Studio`.
- Hydrate persisted SQLite history into the in-process loop/context history after restart.
- Ensure any fallback remains loopback/local and does not bypass the authority boundary.
- Add focused tests before proposing promotion.
