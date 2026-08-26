# Sovereign FORBIDDEN / REQUIRED Matrix

**Authority:** Appel420 (Human Root)  
**Lane enforcement:** ara-hardened and all agents  
**Status:** Binding

## FORBIDDEN

```
FORBIDDEN
├── React
├── Meta/Llama
├── Google/Gemini/Firebase/Vertex
├── unauthorized egress
├── HTTP production transport
├── WS production transport
└── unauthenticated execution endpoints
```

| Item | Rule |
|------|------|
| React | No React source, deps, or scaffolding |
| Meta / Llama | No Meta models, SDKs, or Llama stacks |
| Google / Gemini / Firebase / Vertex | No Google cloud AI or Firebase/Vertex paths |
| Unauthorized egress | No outbound calls without owner allow |
| HTTP production transport | Production must not use plain HTTP |
| WS production transport | Production must not use plain WS |
| Unauthenticated execution endpoints | No exec surfaces without auth |

## REQUIRED

```
REQUIRED
├── HTTPS
├── WSS
├── certificate validation
├── mTLS where required
├── signed authorization
├── capability checks
├── visible execution state
├── owner approval for triage repairs
└── SCAR evidence
```

| Item | Rule |
|------|------|
| HTTPS | Production transport encrypted |
| WSS | Production websockets encrypted |
| Certificate validation | No blind trust; validate certs |
| mTLS where required | Mutual TLS on sovereign control planes |
| Signed authorization | Capability grants must be signed |
| Capability checks | Enforce least privilege before action |
| Visible execution state | Jobs/runs must appear in graph; no hidden cancel |
| Owner approval for triage repairs | Deny / Allow once / Always allow before merge on protected paths |
| SCAR evidence | Immutable audit trail for material actions |

## Agent obligation

1. Scan and report violations; do not hide them.
2. Do not introduce FORBIDDEN items.
3. Prefer REQUIRED patterns in all new code and CI.
4. Protected-path changes need explicit owner decision before merge.
