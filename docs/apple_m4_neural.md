          feature/canonical-governance-core
# Overview of the Apple M4 Chip Neural Engine

The Apple M4 chip features a highly advanced Neural Engine, which is a key component designed to enhance performance in artificial intelligence (AI) and machine learning (ML) tasks.

## Performance Capabilities

- **Operations per Second:** The M4 Neural Engine can perform up to 38 trillion operations per second (TOPS).
- **Comparison to Previous Generations:** This performance is more than double that of the M3's Neural Engine, making it significantly faster and more efficient for AI-related tasks.

## Architectural Advantages

- **Unified Memory Architecture:** The M4 chip utilizes a unified memory architecture, allowing the CPU, GPU, and Neural Engine to share the same memory pool. This design reduces latency and improves data processing speeds, which is crucial for running complex AI models efficiently.

## Applications

The enhanced capabilities of the M4 Neural Engine make it particularly effective for:

- **Machine Learning Tasks:** Ideal for applications that require heavy computational power, such as image recognition, natural language processing, and real-time data analysis.
- **Creative Workflows:** Useful in professional applications like video editing, music production, and graphic design, where AI can assist in rendering and processing tasks.

The M4 chip's Neural Engine represents a significant leap in performance, making it a powerful tool for developers and users engaged in AI and machine learning.
=======
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