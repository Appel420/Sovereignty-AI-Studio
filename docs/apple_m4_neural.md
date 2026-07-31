# Apple M4 Neural Engine

Local reference for the Sovereignty AI Studio dashboard.

## Performance

- **Neural Engine:** up to **38 TOPS** (trillion operations per second)
- More than double the M3 Neural Engine for on-device AI workloads

## Architecture

- **Unified memory** shared by CPU, GPU, and Neural Engine
- Lower latency for model inference and on-device training experiments
- Designed for local execution — no cloud required for engine use

## Sovereignty relevance

- Preferred target for offline / ghost-mode inference
- Training on the Neural Engine is restricted by Apple’s default software path (CoreML / Metal inference-first)
- External public reports (June 2026) describe reverse-engineered paths that expose additional training throughput outside the official stack; those remain experimental and are **not** invoked by this repository’s default CI or dashboard

## Dashboard fields

| Field | Value |
|-------|--------|
| tops | 38 |
| memory | unified |
| doc | `docs/apple_m4_neural.md` |

This file is a build input for `scripts/validate-local-dashboard.py` and the `/api/local-status` endpoint.
