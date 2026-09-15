"""Fail-closed mTLS policy helpers for the Node bridge.

TLS certificate validation is performed by Node's TLS stack. This module
centralizes the policy decision that client authentication is mandatory when
mTLS is enabled and prevents an environment override from silently weakening
production enforcement.
"""
from __future__ import annotations

import os


class MTLSConfigurationError(ValueError):
    pass


def require_client_auth(*, tls_enabled: bool, ca_configured: bool, production: bool) -> bool:
    if not tls_enabled:
        if production:
            raise MTLSConfigurationError("production TLS endpoint is not configured")
        return False
    if production and not ca_configured:
        raise MTLSConfigurationError("production mTLS requires a trusted client CA")
    return ca_configured


def reject_unauthorized(*, production: bool) -> bool:
    """Return the only safe TLS setting for the current deployment class."""
    if production:
        return True
    return os.getenv("TLS_REJECT_UNAUTHORIZED", "1") != "0"
