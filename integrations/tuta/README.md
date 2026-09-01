# Tuta MCP Connector (tutamcp)

Local-first, E2E-encrypted Tuta mail access for the Sovereignty stack.

**No credentials in this repo.** Secrets live in a `chmod 600` file on the host.

## Sources (unofficial, not affiliated with Tutao GmbH)

- tutamcp: https://github.com/peix2/tutamcp-public
- tutaproxy: https://github.com/peix2/tutaproxy-public

Requires tutaproxy >= v1.3.15 (TOTP/2FA support).

## Why this fits the vault

- Tuta has no official IMAP/POP3/SMTP (by design, E2E).
- tutaproxy runs locally and decrypts on your machine.
- tutamcp exposes 30 MCP tools (mail, calendar, contacts, drive) over stdio.
- Everything stays on loopback. No Gmail, no Outlook, no third-party account ever touches the vault.

## Quickstart (Docker)

```bash
git clone https://github.com/peix2/tutamcp-public.git
cd tutamcp-public
docker build --build-arg TUTAPROXY_REF=v1.3.15 -t tutamcp .
```

Create credentials (chmod 600):

```
TUTA_EMAIL=Appel420@tutamail.com
TUTA_PASSWORD=yourpassword
# TUTA_TOTP_SECRET=...   # only if 2FA enabled
```

## Register in Grok / Claude

See `mcp.example.json` in this directory.

## Security notes

- tutaproxy telemetry is ON by default. Set `TUTAPROXY_TELEMETRY=false`.
- Do not expose proxy ports beyond 127.0.0.1.
- Treat TUTA_TOTP_SECRET like a password.
- This integration is opt-in and local-only. It does not alter the Diamond Lattice contract or SCAR chain.
