# ADR-0001: Canonical Runtime State

- **Status:** Accepted
- **Date:** 2026-07-28
- **Decision owners:** Human device owner / Root Authority
- **Related specification:** [Sovereignty AI Specification v1.0](../SOVEREIGNTY_AI_SPECIFICATION_v1.0.md)

## Context

Sovereignty AI must support idle operation, family conversation, phone calls, background speech, active missions, disconnected operation, and controlled network modes without confusing temporary assistant activity with the platform's operating foundation.

A single generic concept of “state” is ambiguous. Treating idle behavior as “without state” could incorrectly permit operation without verified authority, policy, identity, trust anchors, or audit infrastructure. Conversely, treating every interaction as an active mission could cause unwanted execution and permanent memory creation.

## Decision

The platform separates state into two distinct categories:

### Canonical Runtime State

Canonical Runtime State is always required while the platform is operating. It includes Root Authority, identity data, policy configuration, vault metadata, trust anchors, cryptographic key references, `SCARLedger`, the participant registry, workspace index, and market-cache metadata.

At boot, the platform loads and verifies this state before starting authority, policy, vault, participant, provider, network, or dashboard services. Missing, invalid, stale, or unverifiable state causes fail-closed behavior, local evidence, and an owner alert when possible.

### Mission State

Mission State is transient. It determines whether and how the assistant may act, but it never grants authority. The context engine uses `NO ACTIVE MISSION` and `ACTIVE MISSION`; canonical state remains loaded throughout both states and during transitions.

An owner-authenticated wake event may transition the context into an active mission. Mission completion returns the context to `NO ACTIVE MISSION` without deleting or weakening canonical state.

## Consequences

### Positive

- Authority and policy remain available during idle operation.
- Background conversation cannot silently become mission execution.
- Startup integrity can be tested independently from mission detection.
- Offline and degraded operation have a clear safety foundation.
- Providers and network clients can be blocked until canonical state and policy are verified.
- Memory and mission behavior can evolve without changing the authority model.

### Trade-offs

- Implementations must maintain and verify a persistent local state store.
- Startup has additional validation stages.
- The context engine must distinguish mission state from canonical runtime state.
- Tests must cover both invalid canonical state and inactive mission behavior.

## Rejected alternatives

### “Without state” as the idle state

Rejected because it implies that the runtime may operate without authoritative, verified canonical state.

### Mission state as authority state

Rejected because temporary activity must never grant or expand authority.

### Provider-managed state as canonical state

Rejected because identity, authority, policy, and evidence must not depend on provider APIs or network availability.

## Required verification

Implementations must demonstrate:

- missing canonical state denies startup;
- invalid, stale, or unverifiable canonical state produces local evidence and fails closed;
- valid canonical state permits startup to proceed in the specified order;
- inactive mission denies mission execution;
- active mission actions remain policy-bound;
- canonical state remains available across mission transitions;
- provider and network initialization cannot occur before `PolicyEngine` succeeds.

## Supersession

A future ADR may supersede this decision only if it preserves the invariant that verified canonical runtime state is required for operation and that mission state never grants authority.
