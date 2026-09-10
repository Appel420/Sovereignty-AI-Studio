# Diamond Fold + Apple Silicon acceleration boundary

## Status
Experimental integration boundary. The Diamond Core authority contract remains authoritative.

## Rules

- Fold is an external consumer of Diamond Core; it is not embedded in the core identity/provenance model.
- Every Fold step must cross one atomic `authorize_and_commit_step` boundary.
- No traversal-local capability or epoch cache may authorize work.
- Metal/unified memory is a physical placement mechanism, never an authority mechanism.
- An MTLBuffer, Core ML object, ANE execution request, or memory tier cannot grant or widen authority.
- ANE integration is optional and fail-closed when no approved backend is installed.
- Memory windows remain the consumer-visible limit; physical capacity is opaque.
- Any failed authority decision produces denial evidence and no execution side effect.

## Apple Silicon mapping

`MemoryWindow` -> bounded `DiamondMemoryHandle` -> Apple Silicon shared memory / GPU resource.

The shared-memory adapter uses Metal `storageModeShared` where available. The adapter does not expose physical addresses and carries the Diamond ObjectID alongside the bounded byte count.

The ANE boundary is represented by `DiamondInferenceBackend`. A concrete Core ML/ANE implementation must be attached behind this protocol and must receive only an already-authorized bounded input. It must not perform authorization itself or bypass the authority store.

## Fold mapping

`DiamondFoldTraversal` owns traversal state and orientation (`inward` / `outward`). It has no capability-management API. Each step invokes the single atomic authority operation. A failed step moves the traversal to `interrupted`; subsequent steps cannot execute.

## Gate

Acceleration is not considered production-ready until:

1. Diamond Core contract tests are green.
2. Fold race tests I-FOLD-012 through I-FOLD-016 are green.
3. Metal adapter tests prove object-ID/byte-window bounds are enforced.
4. ANE adapter tests prove missing backend fails closed.
5. Integration tests prove physical relocation does not alter ObjectID or authority state.
6. CI builds the iOS target with the acceleration boundary present.
