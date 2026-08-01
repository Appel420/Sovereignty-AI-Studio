# Attention Kernel API Contract

Version: 1.0
Status: Production Baseline

That contract is internally consistent and appropriate as a production baseline. One final recommendation is to separate API contracts from implementation choices, so future optimizations (SIMD, ANE offload, GPU kernels) do not inadvertently change observable behavior.

## API contract (must never change)

These are externally visible guarantees:

* Configuration validation occurs before any tensor access.
* `cfg.dim == n_heads * head_dim` is mandatory.
* Invalid configurations return `ANE_ERR_CONFIG`.
* No out-of-bounds memory access is permitted.
* Softmax normalization never produces NaN/Inf.
* Temporary memory complexity is O(S).
* The backward pass is numerically consistent with the forward pass.
* Error codes remain stable.

## Implementation contract (may evolve)

These are optimization details that can change without affecting correctness:

* Row pointers versus direct indexing.
* SIMD vectorization.
* Loop ordering.
* Cache blocking.
* ANE/GPU dispatch.
* Memory alignment.
* Prefetching.
* Parallel execution.

Keeping those layers separate allows replacing the implementation while preserving the same regression suite.

## Regression invariants

In addition to functional tests, assert invariants directly:

### Configuration

✓ `expected_dim == stride`

✓ `stride > 0`

### Memory

✓ scores allocation == S elements

✓ no allocation inside attention loops

### Numerics

✓ probabilities finite

✓ probabilities sum to 1 ± ε

### Backward

✓ finite gradients

✓ finite-difference error < 1e-4

### Complexity

✓ temporary memory O(S)

✓ attention computation O(S² × n_heads × head_dim)

## Runtime assertions

For debug builds, assertions complement error returns:

```c
assert(expected_dim == stride);
assert(scores != NULL);
assert(!isnan(sum));
assert(!isinf(sum));
```

These should compile away in release builds while helping detect programming errors during development.

## Empty-sequence policy

`S <= 0` is rejected unless empty sequences are explicitly supported by a future contract revision.

## Versioning

To prevent future ambiguity, document the contract with an explicit version identifier:

```text
Attention Kernel Contract
Version: 1.0
Status: Production Baseline
```

Future revisions (for example SIMD or ANE-specialized implementations) can target Contract v1.0 while changing only internal mechanics.

This yields a clean separation:

* Specification — defines required behavior.
* Reference implementation — satisfies the specification.
* Regression suite — proves conformance.
* Optimized implementations — interchangeable as long as they pass the same contract tests.

That structure makes the attention kernel maintainable across CPU, GPU, and ANE implementations without changing its externally observable semantics.
