"""
Fail-closed trust gate for the DOD INTEROPERABILITY ROOT CA 2.

This root is recognized for analysis only. It is never trusted by default,
requires explicit consent, and quarantines any PEM/fingerprint mismatch.
"""

from __future__ import annotations

import base64
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

PEM = """-----BEGIN CERTIFICATE-----
MIICbjCCAdOgAwIBAgIBATANBgkqhkiG9w0BAQsFADByMQswCQYDVQQGEwJVUzEY
MBYGA1UEChMPVS5TLiBHb3Zlcm5tZW50MQwwCgYDVQQLEwNQS0kxDzANBgNVBAsT
BkRPREpRMSwwKgYDVQQDEyNET0QgSU5URVJPUEVSQUJJTElUWSBST09UIENBIDIw
HhcNMTAxMTI5MTQyNTEwWhcNMzAxMTI0MTQyNTEwWjByMQswCQYDVQQGEwJVUzEY
MBYGA1UEChMPVS5TLiBHb3Zlcm5tZW50MQwwCgYDVQQLEwNQS0kxDzANBgNVBAsT
BkRPREpRMSwwKgYDVQQDEyNET0QgSU5URVJPUEVSQUJJTElUWSBST09UIENBIDIw
ggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC/xuCDk+YLgynoKDt2SuCs
jJ60VcPfGH7is3NytGihZtiYY+q+j17ADhGtf9LzpSUv7n6j2JCNSCFg098/hRv8
Qxe9rM3R/uAt/r1GHz6YVojfB0ySBLQF1RXgmqTDUdMKeNg8/Fwc5c0jSZdQPrG0
tqJTUiQJMQOME+fpTcP7A9wCo1rVbWuvFivUTv57oEE47UuvJjW1nIlpDuklzbFN
M6+ObWWRKOXc/XLo+KYxM5L/8AKjUE6Bwfj06pUpCaXaq2Bh/eq5T0oxipdm+MMQ
0tKGoyJD07t5Jy5vtbJl5UuNSa8QsdJbdXcQdOMW8iRneAy29jYPQu//o8C7xl61
AgMBAAGjQjBAMA8GA1UdEwEB/wQFMAMBAf8wHQYDVR0OBBYEFF/4rhOLkit5kkGj
dlwsgZ6axZx4MA4GA1UdDwEB/wQEAwIBhjANBgkqhkiG9w0BAQsFAAOCAQEAUyKL
L/dezOY4MizE80RLGcjgNLW8TUsJP6sPP7LgtPig3thXED8/LNK/NDeAU03jWRzJ
gIW+o40UpU9QWIqstkzCVuzh8512O73hUCCz7C6Tt+dPGfb4UsKHSFPiimI0R1TW
ET1RP5ejpjWC8s4hC73OJbsU9Ycc7fGSu/V+VEfIbMOwwq3CWAt4DA8fYKWlmQTw
CfMv4kuYuRgA7HqUS/o2CumHH0e5OSmRY3WiJOEEMpgzSV3nP5jkFvO4uVRqIrwd
LTdLE5GWFGuFKBEl19XSCmtf+1yQFoZK1JFA9QjHdFAmRLET4kU5q2XrRziBxvOL
/4ZKhMfkdCdIiBMPng==
-----END CERTIFICATE-----"""

ROOT = {
    "id": "dod-interop-root-ca-2",
    "name": "DOD INTEROPERABILITY ROOT CA 2",
    "fingerprint_sha1_claimed": "522E1BF5BE152FA98BED4F01AA441D01092D5A31",
    "subject_dn": "CN=DOD INTEROPERABILITY ROOT CA 2,OU=PKI,OU=DOD,O=U.S. GOVERNMENT,C=US",
    "valid_from": "2010-11-29T14:25:10Z",
    "valid_to": "2030-11-24T14:25:10Z",
    "key_type": "RSA-2048",
    "signature_algorithm": "SHA256withRSA",
    "is_ca": True,
    "path_length": "UNLIMITED",
    "trust_level": "recognized_external",
    "trusted_by_default": False,
    "requires_explicit_consent": True,
    "pem": PEM,
}


def pem_sha1(pem: str) -> str:
    """Return the normalized DER SHA-1 fingerprint for a PEM certificate."""
    body = re.sub(r"-----BEGIN CERTIFICATE-----|-----END CERTIFICATE-----|\s+", "", pem)
    return hashlib.sha1(base64.b64decode(body, validate=True)).hexdigest().upper()


def now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class Store:
    """Immutable-at-construction registry for recognized external roots."""

    def __init__(self) -> None:
        self.roots = {ROOT["id"]: dict(ROOT)}
        for root in self.roots.values():
            try:
                root["fingerprint_sha1_pem_computed"] = pem_sha1(root["pem"])
                root["pem_error"] = None
            except (ValueError, TypeError) as error:
                root["fingerprint_sha1_pem_computed"] = None
                root["pem_error"] = str(error)
            root["metadata_integrity_ok"] = (
                root["fingerprint_sha1_pem_computed"] is not None
                and root["fingerprint_sha1_pem_computed"] == root["fingerprint_sha1_claimed"]
            )

    @staticmethod
    def _fp(value: object) -> str:
        return str(value).replace(":", "").replace(" ", "").strip().upper()

    def get(self, query: object) -> Optional[dict]:
        """Find a root by identifier, label, subject DN, or SHA-1 fingerprint."""
        query = str(query or "").strip()
        query_fingerprint = self._fp(query)
        for root in self.roots.values():
            for candidate in (
                root.get("id", ""),
                root.get("name", ""),
                root.get("subject_dn", ""),
                root.get("fingerprint_sha1_claimed", ""),
                root.get("fingerprint_sha1_pem_computed", ""),
            ):
                if query == str(candidate).strip() or query_fingerprint == self._fp(candidate):
                    return root
        return None

    def date(self, query: object) -> dict:
        """Check whether the registered root is currently within its validity window."""
        root = self.get(query)
        if not root:
            return {"ok": False, "decision": "QUARANTINE_UNKNOWN_ROOT"}

        checked_at = datetime.now(timezone.utc)
        valid_from = datetime.fromisoformat(root["valid_from"].replace("Z", "+00:00"))
        valid_to = datetime.fromisoformat(root["valid_to"].replace("Z", "+00:00"))
        valid = valid_from <= checked_at <= valid_to
        return {
            "ok": valid,
            "valid_from": root["valid_from"],
            "valid_to": root["valid_to"],
            "checked_at": checked_at.isoformat(),
            "decision": "DATE_WINDOW_VALID" if valid else "QUARANTINE_ROOT_OUTSIDE_VALIDITY",
        }

    def meta(self, query: object) -> dict:
        """Fail closed when the supplied PEM and its claimed fingerprint differ."""
        root = self.get(query)
        if not root:
            return {"ok": False, "decision": "QUARANTINE_UNKNOWN_ROOT"}
        valid = root["metadata_integrity_ok"] is True
        return {
            "ok": valid,
            "claimed_sha1": root["fingerprint_sha1_claimed"],
            "computed_pem_sha1": root["fingerprint_sha1_pem_computed"],
            "pem_error": root["pem_error"],
            "decision": (
                "ROOT_METADATA_INTEGRITY_OK"
                if valid
                else "QUARANTINE_ROOT_METADATA_MISMATCH"
            ),
        }

    def decision(self, query: object, consent: bool = False) -> dict:
        """Return an explicit trust decision; this store never marks roots trusted."""
        root = self.get(query)
        metadata = self.meta(query)
        date_status = self.date(query)
        if not root:
            final, recognized, level, reason = (
                "QUARANTINE",
                False,
                "unknown",
                "Root is not registered.",
            )
        else:
            recognized = True
            level = root.get("trust_level", "unknown")
            reason = "Recognized for analysis only; explicit consent required before trust."
            if not metadata["ok"]:
                final = "QUARANTINE_ROOT_METADATA_MISMATCH"
            elif not date_status["ok"]:
                final = "QUARANTINE"
            elif root.get("trusted_by_default") is True:
                final = "ALLOW"
            elif root.get("requires_explicit_consent") and consent:
                final = "ALLOW_WITH_EXPLICIT_CONSENT"
            else:
                final = "QUARANTINE_CONSENT_REQUIRED"
        return {
            "recognized": recognized,
            "trusted": False,
            "requires_explicit_consent": True,
            "trust_level": level,
            "decision": (
                "RECOGNIZED_EXTERNAL_CONSENT_REQUIRED"
                if recognized
                else "QUARANTINE_UNKNOWN_ROOT"
            ),
            "reason": reason,
            "metadata_integrity": metadata,
            "date_status": date_status,
            "explicit_consent": consent,
            "checked_at": now(),
            "final": final,
        }

    def public_roots(self) -> list[dict]:
        """Return public metadata without certificate bodies."""
        return [{key: value for key, value in root.items() if key != "pem"} for root in self.roots.values()]
