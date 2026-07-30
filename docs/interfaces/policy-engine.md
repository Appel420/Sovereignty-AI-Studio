# PolicyEngine

## Purpose

Authorize capabilities according to canonical state, Root Authority, participant identity, data classification, mission state, and runtime mode.

## Inputs

- requested capability
- participant identity
- runtime mode
- mission state
- workspace
- data classification
- requested scope and duration
- owner approval reference

## Outputs

- `ALLOW`
- `DENY`
- `REQUIRE_APPROVAL`

## Failure behavior

If canonical state or the PolicyEngine is unavailable, network and provider capabilities are disabled. The request is denied and a `POLICY_ENGINE_UNAVAILABLE` or equivalent event is appended to `SCARLedger`.

## Normative rules

- Default decision is `DENY`.
- Offline denies external network and provider APIs.
- Hybrid allows only approved public retrieval; private upload is denied by default.
- Online remains policy- and audit-controlled.
- Higher network modes and sensitive actions require explicit owner approval.
- No external client initializes before policy success.

## Audit requirements

Every decision records timestamp, request ID, participant ID, capability, mode, policy version, decision, and reason. Private payloads and secrets are excluded.
