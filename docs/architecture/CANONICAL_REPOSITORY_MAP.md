# Canonical Repository Map

## Purpose

This document defines the repository boundaries used by Sovereignty-AI-Studio.
It is an integration contract, not a second authority plane.

The repository registry identifies **where a capability belongs**. It does not
authorize that capability, execute it, or replace the owning repository.

## System topology

```text
Human Owner
    |
    v
Sovereignty-AI-Gate
    |  authority / identity / policy / capability
    v
Coordination + Integration
    |
    +-------------------+-------------------+------------------+
    |                   |                   |                  |
    v                   v                   v                  v
Studio              Hawking/Mesh        DevAssist420      Risk/Assurance
integration         transport           execution          assurance
    |                   |                   |                  |
    +-------------------+-------------------+------------------+
                            |
                            v
                     SCAR / Evidence
                            |
                            v
                       Owner-visible
```

## Repository responsibilities

| Repository | Domain | Owns | Does not own |
|---|---|---|---|
| `Appel420/Sovereignty-AI-Gate` | Authority | identity, authorization, policy, capability decisions | dashboard, execution implementation |
| `Appel420/Sovereignty-AI-Studio` | Integration | dashboard, adapters, coordination contracts, local CI/evidence projection | root authority, provider authority, execution implementation |
| `Appel420/DevAssist420` | Execution/client | authorized execution and client-facing services | root authority |
| Hawking/mesh component | Transport | authenticated runtime transport and mesh communication | authorization |
| `Appel420/Sovereignty-Risk-Engine-Runtime-Assurance` | Assurance | risk evaluation and runtime assurance | root authority |
| SCAR/AUDIT/REPMHL components | Evidence | provenance and immutable evidence | authorization |

## Runtime invariant

Repository availability is not authorization.

```text
repository access != authority
file availability != permission
registry entry != capability grant
route selection != authorization
execution receipt != authorization
SCAR evidence != authorization
```

## Network invariant

Runtime availability and network policy are independent dimensions.

Ghost mode does **not** mean that the backend, Hawking runtime, or mesh is
stopped. A runtime may remain operational and maintain the owner communication
channel while individual outbound operations are evaluated by policy.

```text
RUNTIME
  running
  owner channel available
  Hawking available
  mesh available

NETWORK
  destination/capability evaluated per operation
  telemetry policy evaluated independently
  egress policy evaluated independently
```

## Integration rule

Studio may consume a capability declared by another repository, but it must
resolve the owning repository and its interface before attempting integration.
The consumer never manufactures an authority decision.

## Evidence rule

Cross-repository findings identify:

- the observed component;
- the owning repository;
- the consumed interface/capability;
- the policy or contract being evaluated;
- the evidence reference;
- the resulting integration status.

A finding is not converted into a provider accusation or an authority decision
by the registry consumer.

## Promotion rule

`main` and `Collaboration` remain owner-controlled. Development lanes are
separate from integration and production. Repository changes must retain their
branch, lease, and evidence provenance.
