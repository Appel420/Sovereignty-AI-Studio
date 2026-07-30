# Network Policy

The active local runtime is offline-first and loopback-only.

## Enforced defaults

- `default_mode`: `offline`
- Services bind only to `127.0.0.1` or `::1`.
- LAN binding is disabled.
- Global IPv6 binding is disabled.
- Unsolicited inbound IPv6 is denied by default.
- External network access requires an explicit policy decision.

## Service map

| Service | Host | Port |
|---|---|---:|
| Python bridge | `127.0.0.1` | `9897` |
| Dashboard | `127.0.0.1` | `9898` |
| Node bridge | `127.0.0.1` | `9899` |

## Validation

Run:

```bash
python3 scripts/validate-network-policy.py
```

The validator rejects non-loopback bindings, invalid ports, non-offline defaults, and non-contiguous IPv4 netmask diagnostics.

A private LAN address is not automatically trusted. `192.168.1.0/24` and `fe80::/10` are local scopes, not authority scopes. Global IPv6 addresses require policy approval and should not be used for service binding.
