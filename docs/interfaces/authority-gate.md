# AuthorityGate

## Purpose

Enforce the human owner as the only Root Authority and authorize explicit, scoped capabilities.

## Inputs

- participant identity
- requested action and scope
- runtime mode
- mission state
- owner approval, if required
- capability expiry

## Outputs

- `ALLOW`
- `DENY`
- `REQUIRE_APPROVAL`
- scoped capability on approval

## Failure behavior

Unknown participants, implicit delegation, authority mutation requests, expired approvals, and unavailable authority state are denied.

## Rules

AI participants are advisory by default. They may request approval but cannot grant it, modify Root Authority, or alter policy.

## Audit requirements

Record participant ID, action, scope, decision, approval reference, expiry, policy version, and reason. Never record credentials, private keys, or raw private payloads.
