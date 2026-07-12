# Offline runtime and transport policy

The default deployment is loopback-only: `SG_OFFLINE_MODE` is enabled unless
explicitly set to `0`, and the Node bridge refuses wildcard (`0.0.0.0`) binds.
It uses `127.0.0.1` by default. External requests are denied and recorded by
the bridge's `/api/network/status` endpoint.

## TLS

Use `SG_TLS_MODE=local-ca` for air-gapped and local-network deployments. The
operator provisions `TLS_CERT` and `TLS_KEY` from their private CA and installs
that CA only on trusted devices.

Let’s Encrypt is an optional public-deployment mode only:

```text
SG_OFFLINE_MODE=0
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
