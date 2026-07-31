# Data Classification

| Class | Examples | Default location | Network policy |
|---|---|---|---|
| Authority | Root ownership, permissions, approvals | Local protected state | Never leaves without explicit export |
| Private | Vault, prompts, conversations, memory, documents, credentials | Encrypted local vault/keystore | Never leaves by default |
| Public | Releases, pricing, benchmarks, advisories, availability | Local market cache | Refreshable under policy |
| Evidence | SCAR events, hashes, signatures | Local append-only ledger | Signed export only |
| Workspace Artifact | Code, notes, approved outputs | Scoped local workspace | Export only through policy |

## Handling rules

- Classification is determined before an operation is authorized.
- Private data is not public market intelligence.
- Raw secrets, session keys, and private payloads are excluded from evidence.
- Mixed-content requests are treated as private unless a policy-approved minimization step creates a public-safe projection.
- Unknown classification results in `DENY`.
