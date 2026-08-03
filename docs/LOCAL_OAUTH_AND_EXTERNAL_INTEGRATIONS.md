# Local OAuth and external integration visibility

The canonical local OAuth path is:

```text
config/local-oauth-policy.json
  -> scripts/oauth_local_generator.py --dry-run
  -> local device artifacts only
```

The local OAuth issuer is Ed25519-based, makes no network calls, and external
OAuth is disabled by policy. `security_backend.py` contains a separate legacy
`/api/oauth/generate` endpoint; it is not the canonical local OAuth path and
must not be treated as enabled merely because the file exists.

The local dashboard status now exposes a read-only inventory of:

- GitHub API and GitHub URL references;
- Google/GCP URL references;
- Terraform files;
- OAuth references and whether they are local or external;
- workflow files with automatic triggers or hosted-runner text.

This inventory does not contact any destination. It exists so integrations are
visible and owner-controllable instead of hidden in UI code.

Run locally:

```bash
python3 scripts/audit-external-integrations.py
python3 scripts/validate-local-oauth.py
LOCAL_CI_FOCUSED_ONLY=1 ./scripts/local-ci.sh
```

GitHub repository browsing in the legacy dashboards uses direct browser calls
to `https://api.github.com`. That is an external route and must be shown as
owner-approved rather than presented as local/offline operation.
