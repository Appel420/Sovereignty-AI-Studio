# SGHv119 cleanup checkpoint

The cleanup is being performed in bounded stages so the existing visual dashboard is preserved.

## Stage completed

- Canonical runtime manifest added.
- Shared transport boundary added.
- Hawking encryption and signature verification added.
- Trusted-fingerprint policy added.
- Bootstrap module added for one Hawking runtime instance.
- Local CI checks the bootstrap module.

## Next surgical edit in the monolithic HTML

Load these scripts exactly once, in this order, before the dashboard's application scripts:

```html
<script src="frontend/runtime/hawking-channel.js"></script>
<script src="frontend/runtime/sg-hawking-integration.js"></script>
<script src="frontend/runtime/sghv119-bootstrap.js"></script>
```

Then remove only duplicate ownership blocks from the HTML:

- inline `SovereignHawkingChannel` definitions;
- inline Hawking status-element creation;
- duplicate `_SG_BRIDGE_STATUS` creation;
- duplicate retry/keepalive loops;
- local-mode fetch patches that reject approved loopback requests;
- duplicate error-to-bridge fallback paths.

Do not remove panel markup, role cards, styles, or visual controls.

## Safety check

Before editing the monolith, run:

```bash
python3 scripts/report-dashboard-duplicates.py
```

The report is read-only. It identifies the remaining duplicate regions without rewriting the file.
