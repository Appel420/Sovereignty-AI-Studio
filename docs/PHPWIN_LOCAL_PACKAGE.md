# PHPWin local package

This package is configured for the iPhone PHPWin workspace and is designed to
run on loopback HTTPS only.

## Modes

```text
local  -> hybrid after a local failure or explicit owner choice
hybrid -> online only with X-Sovereignty-Owner-Approval: OWNER_APPROVED
online -> never selected automatically
```

## Local entrypoint

```text
index.php
```

## Diagnostics

`diagnostics/phpinfo.php` is disabled by default. To enable it, set
`diagnostics.phpinfo_enabled` to `true` in `phpwin.json`, keep the server on
loopback, and send:

```text
X-Sovereignty-Diagnostics: OWNER_LOCAL_ONLY
```

## No secrets

Do not commit OAuth credentials, private keys, generated audit logs, or device
storage. This package contains only local configuration and bootstrap code.
