# MarketIntelligenceCache

## Purpose

Store normalized public market intelligence locally so the dashboard remains useful offline and never depends on direct provider access.

## Inputs

- public feed item
- source identity
- normalized fields
- validation result
- timestamp
- optional signature

## Outputs

- cached item
- cache status
- last refresh timestamp
- source status
- stale-data indicator

## Failure behavior

A source failure preserves the last valid cache. Empty cache remains a valid dashboard state and must not block navigation, search, filters, or workspaces. Invalid or private feed content is rejected.

## Allowed content

Model releases, provider announcements, pricing, context windows, capabilities, licensing, benchmarks, availability, and security advisories.

## Prohibited content

User prompts, conversations, vault contents, personal memory, credentials, and telemetry.

## Audit requirements

Record source, item identifier, normalization/validation result, timestamp, cache action, and integrity metadata. `FeedAdapter` is a v1.1 extension and feeds this cache; the dashboard never communicates directly with external providers.
