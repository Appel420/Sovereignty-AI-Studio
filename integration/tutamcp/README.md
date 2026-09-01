# Tuta MCP adapter

This directory defines the Sovereignty integration boundary for the external `tutamcp-public` MCP server.

## Classification

- Type: external adapter
- Transport: local Docker stdio
- Network mode: policy-gated external service access through the adapter
- Credentials: host-local only; never committed
- Canonical runtime owner: Sovereignty AI Studio remains the owner; Tuta MCP is not a second runtime owner

Upstream implementation: `peix2/tutamcp-public`.

## Build

Build the upstream image locally:

```bash
git clone https://github.com/peix2/tutamcp-public.git
cd tutamcp-public
docker build --build-arg TUTAPROXY_REF=v1.3.15 -t tutamcp .
```

The pinned `v1.3.15` ref is required when the account uses TOTP/2FA according to the upstream documentation.

## Credentials

Create a host-local file with mode `600`:

```text
TUTA_EMAIL=your@tuta.com
TUTA_PASSWORD=REPLACE_ME
# TUTA_TOTP_SECRET=REPLACE_ME_IF_REQUIRED
```

Never put the file, password, TOTP secret, or any other private state in Git.

## Local MCP registration

For a Grok CLI stdio registration, use:

```bash
grok mcp add tutamcp -- docker run --rm -i \
  -v /absolute/path/to/credentials.env:/creds.env:ro \
  -e TUTAMCP_CREDENTIALS_FILE=/creds.env \
  -e TUTAMCP_ENABLE_MAIL=1 \
  -e TUTAMCP_MAIL_MODE=dedicated \
  -e TUTAMCP_OWNER_EMAIL=your@tuta.com \
  tutamcp
```

If the installed CLI uses `grok` rather than `grok`, substitute the installed executable; the MCP registration remains a local stdio Docker process.

## Sovereignty boundary

The adapter must not receive unrestricted host filesystem access. Mount only the credentials file read-only and only add additional mounts when a separate reviewed contract authorizes them.

Do not add Tuta credentials to Compose defaults, CI variables, repository secrets, logs, images, or test fixtures.
