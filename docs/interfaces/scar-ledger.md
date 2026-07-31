# SCARLedger

## Purpose

Provide an append-only local evidence ledger for policy-relevant runtime events.

## Inputs

- timestamp
- participant identity
- action
- policy/version
- result and reason
- request identity
- bounded metadata

## Outputs

- immutable event ID
- deterministic serialized event
- integrity hash
- verification result

## Failure behavior

A ledger append failure must not be silently ignored. Protected operations fail closed unless the policy explicitly permits a safe degraded mode. Mutation, truncation, malformed serialization, or hash mismatch is a threat condition.

## Required event fields

```text
event_id
timestamp
participant_id
action
policy_version
result
reason
previous_hash
integrity_hash
```

## Privacy rules

Do not record credentials, session keys, private keys, raw prompts, raw documents, vault contents, or raw private payloads. Use references, classifications, and one-way digests where evidence is necessary.

## Verification

Events use deterministic serialization and a chained integrity hash. Verification detects modified, reordered, or truncated entries where checkpoints are available.
