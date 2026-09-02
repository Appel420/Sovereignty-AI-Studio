# SGHV119 Owner Transparency Panel

## Purpose

The Apple/iOS-first panel is a persistent, movable, owner-visible observation surface. It shows runtime provenance and state without granting authority or executing operations.

## Provenance

Observed actions are represented with 5W1H fields plus repository/branch and execution identity:

- WHO: human owner and machine execution agent
- WHAT: operation or observed event
- WHEN: ISO-8601 timestamp
- WHERE: repository and branch
- WHY: request/policy reason
- HOW: capability or observation mechanism
- RESULT: observed outcome
- MODEL: underlying model metadata, when supplied by the runtime

The execution lane remains GitHub Copilot; the model identifier is metadata and never becomes the authorization authority.

## Safety boundary

The panel is read-only by default. UI visibility is not authorization. A future MCP integration must continue to enforce owner approval, capability scope, repository/branch validation, lease validity, policy/risk decision, and SCAR evidence before state-changing execution.

## Platform

The first implementation is browser-based and responsive for Apple/iOS. The runtime contract is intentionally platform-neutral so the same observation schema can later be surfaced on macOS, Windows, and Android without changing authority semantics.
