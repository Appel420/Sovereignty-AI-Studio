# Offline runtime and transport policy

The default deployment is **offline** and loopback-only. `SG_NETWORK_MODE`
selects one of the existing transport modes:

- `offline` (default): loopback-only, no external or LAN requests.
- `hybrid`: loopback plus hosts named in `SG_LOCAL_NETWORK_ALLOWLIST`; it still
  cannot reach the Internet.
- `online`: remote traffic only when `SG_ENABLE_REMOTE_NETWORK=1` is also set.

The browser keeps the corresponding `offline`, `hybrid`, and `online` state.
Hybrid endpoints and online access are session-only, user-approved choices.
The Node bridge refuses wildcard (`0.0.0.0`) binds and uses `127.0.0.1` by
default. Blocked requests are recorded by `/api/network/status`.

## TLS

Use `SG_TLS_MODE=local-ca` for air-gapped and local-network deployments. The
operator provisions `TLS_CERT` and `TLS_KEY` from their private CA and installs
that CA only on trusted devices.

Let’s Encrypt is an optional public-deployment mode only:

```text
SG_NETWORK_MODE=online
SG_ENABLE_REMOTE_NETWORK=1
SG_TLS_MODE=letsencrypt
ACME_DOMAIN=public.example
ACME_EMAIL=operator@example
```

ACME issuance and renewal require an Internet connection and public
reachability. They are unavailable in offline mode; no automatic certificate
request is attempted.

## iPhone voice and emergency mesh

`platform/ios/OfflineVoiceMeshCoordinator.swift` uses
`MultipeerConnectivity` with required transport encryption for nearby peers.
Its `LocalSpeechEngine` and `LocalLanguageModel` protocols intentionally
require bundled, on-device implementations; browser `SpeechRecognition` and
network-backed speech services are not acceptable substitutes.

There is no ability to communicate outside a cave with no reachable peer or
radio path. The device can still perform local voice and model inference. The
host app must display this condition and retain messages locally for a later
peer connection.
