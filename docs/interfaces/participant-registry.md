# ParticipantRegistry

## Purpose

Maintain provider-neutral identities, roles, capabilities, permissions, workspaces, memory allocations, evidence streams, versions, and trust status.

## Inputs

- participant record
- immutable Participant ID
- owner-approved configuration
- lifecycle event

## Outputs

- participant lookup
- validated participant record
- capability and workspace metadata

## Failure behavior

Duplicate IDs, missing identity fields, provider-dependent identity, invalid role, or unauthorized configuration changes are rejected and recorded.

## Audit requirements

Record registration, upgrade, disablement, permission change, and trust-status changes without storing secrets or private payloads.

## Categories

`Human`, `AI`, `Service`, and `System`. AI participants never become human identities or Root Authority.
