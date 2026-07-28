# Local CI Interface

## Purpose

Validate repository integrity using controlled local execution on the self-hosted Linux runner. CI validates repository contracts; CI does not become an authority source and does not grant permissions.

## Inputs

- repository checkout
- local validation scripts
- architecture and interface contracts
- repository integration manifest
- runner identity and commit metadata

## Validation stages

```text
Repository
    |
    v
Self-hosted Runner
    |
    v
Local Validation
    +-- Script integrity
    +-- Python integrity
    +-- Node integrity
    +-- Integration preflight
    |
    v
Allow / Reject
```

## Outputs

- validation pass
- validation failure
- local evidence report containing commit SHA, runner identity, validation results, and timestamp

## Failure behavior

A failed validation stops execution, records local evidence, and does not start services. The validation path must not make remote calls or require hosted infrastructure.

## Audit requirements

Every run records:

- repository commit SHA
- self-hosted runner identity
- operating system
- validation stage results
- UTC timestamp
- final pass/fail status

Evidence is written locally. It must not contain credentials, private keys, raw private payloads, or source contents.

## Authority boundary

CI reports whether declared checks passed. It does not authorize providers, change policy, create credentials, or replace the human Root Authority.
