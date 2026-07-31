# SGHv119 Hawking wiring

The monolithic `SGHv119.html` must load these scripts in this order before creating its dashboard status indicator:

```html
<script src="frontend/runtime/hawking-channel.js"></script>
<script src="frontend/runtime/sg-hawking-integration.js"></script>
```

Then create exactly one integration instance:

```javascript
window.SGHv119HawkingRuntime = SGHv119Hawking.create({
  statusElement: document.getElementById('sgb-hawking'),
  trustedFingerprints: window.SGH_TRUSTED_FINGERPRINTS || []
});

SGHv119HawkingRuntime.init().catch(function (error) {
  console.error('Hawking unavailable:', error.message);
});
```

## Trust behavior

- Empty trusted-fingerprint configuration produces `UNTRUSTED`.
- A fingerprint is `VERIFIED` only when explicitly present in owner-approved configuration.
- Envelope self-reported fingerprints never authorize themselves.
- Private keys and live device identity records must not be committed.

## Duplicate cleanup boundary

The existing monolithic page should remove or disable its duplicate Hawking implementation, duplicate status label, duplicate bridge retry loop, and duplicate transport fallback. Keep one status element and route all Hawking calls through `SGHv119HawkingRuntime`.

This adapter does not claim that HTTPS, WSS, mTLS, satellite, mesh, PQC, X25519, or Ed25519 is active. Those states must come from separate verified runtime adapters.
