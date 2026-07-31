# SCAR Local-First Governance Log

**Log type:** local corrective record  
**Status:** recorded  
**Authority:** Human Owner  
**Network:** disabled  
**External providers:** not contacted  
**Remote listening:** disabled

## Event

- **Event:** Cloud-oriented execution was proposed despite the local-first rule.
- **Classification:** `security`
- **Actor:** `device`
- **Decision:** `DENY`
- **Reason:** Local-first authority and execution boundary was not preserved.
- **Scope:** Current device-local registry, dashboard, CI, and coding-agent workflow.
- **Evidence:** This append-only record.

## Corrective rule

All default execution remains device-local and offline. No cloud runner, remote agent, provider API, hosted scanner, CDN, registry, remote wake-word service, remote TTS service, or external memory service may be required or contacted.

Cloud or provider access is denied unless the Human Owner explicitly authorizes it through the local policy boundary. A suggestion, tool availability, repository integration, or credential does not constitute authorization.

## Listening boundary

No background listening is enabled by this feature. Wake-word recognition remains:

```json
{
  "wake_word": "hey ara",
  "recognition": "local_engine_required",
  "remote_recognition": false,
  "status": "not_configured"
}
```

No claim is made that a local wake-word engine or TTS engine is installed or active.

## Required behavior

1. Record local evidence before any protected operation.
2. Deny external execution by default.
3. Do not initialize external clients before policy approval.
4. Do not silently substitute cloud execution for unavailable local execution.
5. Preserve local functionality and report an explicit failure when a local dependency is missing.
6. Never record credentials, private payloads, session keys, or raw audio in this log.

## Next state

`NO ACTIVE MISSION` until the Human Owner explicitly authorizes a local implementation task. Any future implementation must use local files, local tests, local logs, and the self-hosted/local execution boundary only.
