from pathlib import Path
import zipfile, hashlib, base64, re, json, subprocess, sys, shutil

base = Path("/mnt/data/validator_rootstore_dod")
if base.exists():
    shutil.rmtree(base)
(base / "validator" / "roots").mkdir(parents=True)
(base / "tests").mkdir(parents=True)

SUPPLIED_FP = "522E1BF5BE152FA98BED4F01AA441D01092D5A31"

pem = """-----BEGIN CERTIFICATE-----
MIICbjCCAdOgAwIBAgIBATANBgkqhkiG9w0BAQsFADByMQswCQYDVQQGEwJVUzEY
MBYGA1UEChMPVS5TLiBHb3Zlcm5tZW50MQwwCgYDVQQLEwNQS0kxDzANBgNVBAsT
BkRPREpRMSwwKgYDVQQDEyNET0QgSU5URVJPUEVSQUJJTElUWSBST09UIENBIDIw
HhcNMTAxMTI5MTQyNTEwWhcNMzAxMTI0MTQyNTEwWjByMQswCQYDVQQGEwJVUzEY
MBYGA1UEChMPVS5TLiBHb3Zlcm5tZW50MQwwCgYDVQQLEwNQS0kxDzANBgNVBAsT
BkRPREpRMSwwKgYDVQQDEwNQS0kxDzANBgNVBAsTBkRPREpRMSwwKgYDVQQDEyNE
T0QgSU5URVJPUEVSQUJJTElUWSBST09UIENBIDIwggEiMA0GCSqGSIb3DQEBAQUA
A4IBDwAwggEKAoIBAQC/xuCDk+YLgynoKDt2SuCsjJ60VcPfGH7is3NytGihZtiY
Y+q+j17ADhGtf9LzpSUv7n6j2JCNSCFg098/hRv8Qxe9rM3R/uAt/r1GHz6YVojf
B0ySBLQF1RXgmqTDUdMKeNg8/Fwc5c0jSZdQPrG0tqJTUiQJMQOME+fpTcP7A9wC
o1rVbWuvFivUTv57oEE47UuvJjW1nIlpDuklzbFNM6+ObWWRKOXc/XLo+KYxM5L/
8AKjUE6Bwfj06pUpCaXaq2Bh/eq5T0oxipdm+MMQ0tKGoyJD07t5Jy5vtbJl5UuN
Sa8QsdJbdXcQdOMW8iRneAy29jYPQu//o8C7xl61AgMBAAGjQjBAMA8GA1UdEwEB
/wQFMAMBAf8wHQYDVR0OBBYEFF/4rhOLkit5kkGjdlwsgZ6axZx4MA4GA1UdDwEB
/wQEAwIBhjANBgkqhkiG9w0BAQsFAAOCAQEAUyKLL/dezOY4MizE80RLGcjgNLW8
TUsJP6sPP7LgtPig3thXED8/LNK/NDeAU03jWRzJgIW+o40UpU9QWIqstkzCVuzh
8512O73hUCCz7C6Tt+dPGfb4UsKHSFPiimI0R1TWET1RP5ejpjWC8s4hC73OJbsU
9Ycc7fGSu/V+VEfIbMOwwq3CWAt4DA8fYKWlmQTwCfMv4kuYuRgA7HqUS/o2CumH
H0e5OSmRY3WiJOEEMpgzSV3nP5jkFvO4uVRqIrwdLTdLE5GWFGuFKBEl19XSCmtf
+1yQFoZK1JFA9QjHdFAmRLET4kU5q2XrRziBxvOL/4ZKhMfkdCdIiBMPng==
-----END CERTIFICATE-----"""
# Note: PEM is preserved from the user's supplied root material as the validator input.
# The computed fingerprint is deliberately checked against the supplied metadata.
body = re.sub(r"-----BEGIN CERTIFICATE-----|-----END CERTIFICATE-----|\s+", "", pem)
computed_fp = hashlib.sha1(base64.b64decode(body)).hexdigest().upper()
metadata_ok = computed_fp == SUPPLIED_FP

(base / "validator" / "__init__.py").write_text('"""Validator package."""\n')
(base / "validator" / "roots" / "__init__.py").write_text('"""Root registry."""\n')
(base / "validator" / "roots" / "dod_interop_root.py").write_text(f'''"""
DOD INTEROPERABILITY ROOT CA 2.

Security posture:
    recognized_external only
    not trusted by default
    explicit consent is required
    metadata/Pem fingerprint mismatch is a hard quarantine condition
"""

DOD_INTEROP_ROOT_CA_2 = {{
    "id": "dod-interop-root-ca-2",
    "name": "DOD INTEROPERABILITY ROOT CA 2",
    "fingerprint_sha1": "{SUPPLIED_FP}",
    "fingerprint_sha1_claimed": "{SUPPLIED_FP}",
    "fingerprint_sha1_pem_computed": "{computed_fp}",
    "metadata_integrity_ok": {metadata_ok},
    "subject_dn": "CN=DOD INTEROPERABILITY ROOT CA 2,OU=PKI,OU=DOD,O=U.S. GOVERNMENT,C=US",
    "valid_from": "2010-11-29T14:25:10Z",
    "valid_to": "2030-11-24T14:25:10Z",
    "key_type": "RSA-2048",
    "signature_algorithm": "SHA256withRSA",
    "is_ca": True,
    "path_length": "UNLIMITED",
    "trust_level": "recognized_external",
    "requires_explicit_consent": True,
    "trusted_by_default": False,
    "allowed_for": ["chain_recognition", "certificate_path_analysis", "interoperability_validation"],
    "not_allowed_for": ["silent_trust", "automatic_acceptance", "sovereign_root_replacement", "policy_bypass"],
    "notes": "DoD Interoperability Root CA 2. Valid until 2030. Use only with explicit user consent. If PEM fingerprint and claimed fingerprint differ, quarantine.",
    "pem": """{pem}""",
}}
''')
(base / "validator" / "root_store.py").write_text('''"""
RootStore policy:
known root != trusted root
recognized root != authorized root
valid chain != approved chain
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from validator.roots.dod_interop_root import DOD_INTEROP_ROOT_CA_2

RootRecord = Dict[str, Any]

@dataclass(frozen=True)
class RootDecision:
    recognized: bool
    trusted: bool
    requires_explicit_consent: bool
    trust_level: str
    decision: str
    root_id: Optional[str] = None
    reason: str = ""

class RootStore:
    def __init__(self, roots: Optional[Dict[str, RootRecord]] = None):
        self.roots = roots or {"dod-interop-root-ca-2": DOD_INTEROP_ROOT_CA_2}

    @staticmethod
    def _fp(value: str) -> str:
        return str(value).replace(":", "").replace(" ", "").strip().upper()

    @staticmethod
    def _text(value: str) -> str:
        return str(value).strip()

    def get_root(self, fingerprint_or_name: str) -> Optional[RootRecord]:
        if not fingerprint_or_name:
            return None
        query = self._text(fingerprint_or_name)
        query_fp = self._fp(query)
        for key, root in self.roots.items():
            candidates = [
                key,
                root.get("id", ""),
                root.get("name", ""),
                root.get("subject_dn", ""),
                root.get("fingerprint_sha1", ""),
                root.get("fingerprint_sha1_claimed", ""),
                root.get("fingerprint_sha1_pem_computed", ""),
            ]
            for candidate in candidates:
                if not candidate:
                    continue
                if query == self._text(candidate) or query_fp == self._fp(candidate):
                    return root
        return None

    def metadata_integrity(self, fingerprint_or_name: str) -> Dict[str, Any]:
        root = self.get_root(fingerprint_or_name)
        if not root:
            return {"ok": False, "decision": "QUARANTINE_UNKNOWN_ROOT"}
        ok = bool(root.get("metadata_integrity_ok") is True)
        return {
            "ok": ok,
            "root_id": root.get("id"),
            "claimed_sha1": root.get("fingerprint_sha1_claimed"),
            "computed_pem_sha1": root.get("fingerprint_sha1_pem_computed"),
            "decision": "ROOT_METADATA_INTEGRITY_OK" if ok else "QUARANTINE_ROOT_METADATA_MISMATCH",
        }

    def classify_root(self, fingerprint_or_name: str) -> RootDecision:
        root = self.get_root(fingerprint_or_name)
        if not root:
            return RootDecision(False, False, True, "unknown", "QUARANTINE_UNKNOWN_ROOT", reason="Root is not in registry.")
        trust_level = root.get("trust_level", "unknown")
        root_id = root.get("id") or root.get("name")
        if trust_level == "trusted_by_default" and root.get("trusted_by_default") is True:
            return RootDecision(True, True, False, trust_level, "ALLOW_TRUSTED_ROOT", root_id, "Root is sovereign-policy approved.")
        if trust_level == "recognized_external":
            return RootDecision(True, False, True, trust_level, "RECOGNIZED_EXTERNAL_CONSENT_REQUIRED", root_id, "Recognized for analysis only; explicit consent required.")
        return RootDecision(True, False, True, trust_level, "QUARANTINE_UNAPPROVED_ROOT", root_id, "Known but not approved for trust.")

    def validate_date_window(self, fingerprint_or_name: str, when: Optional[datetime] = None) -> Dict[str, Any]:
        root = self.get_root(fingerprint_or_name)
        if not root:
            return {"ok": False, "decision": "QUARANTINE_UNKNOWN_ROOT", "reason": "Root not found."}
        when = when or datetime.now(timezone.utc)
        valid_from = datetime.fromisoformat(root["valid_from"].replace("Z", "+00:00"))
        valid_to = datetime.fromisoformat(root["valid_to"].replace("Z", "+00:00"))
        ok = valid_from <= when <= valid_to
        return {
            "ok": ok,
            "root_id": root.get("id"),
            "valid_from": root["valid_from"],
            "valid_to": root["valid_to"],
            "checked_at": when.isoformat(),
            "decision": "DATE_WINDOW_VALID" if ok else "QUARANTINE_ROOT_OUTSIDE_VALIDITY",
        }

    def trust_decision(self, fingerprint_or_name: str, explicit_consent: bool = False) -> Dict[str, Any]:
        decision = self.classify_root(fingerprint_or_name)
        meta = self.metadata_integrity(fingerprint_or_name)
        date_status = self.validate_date_window(fingerprint_or_name)
        payload = {**decision.__dict__, "metadata_integrity": meta, "date_status": date_status}
        if not decision.recognized:
            return {**payload, "final": "QUARANTINE"}
        if not meta["ok"]:
            return {**payload, "final": "QUARANTINE_ROOT_METADATA_MISMATCH"}
        if not date_status["ok"]:
            return {**payload, "final": "QUARANTINE"}
        if decision.trusted:
            return {**payload, "final": "ALLOW"}
        if decision.requires_explicit_consent and explicit_consent:
            return {**payload, "final": "ALLOW_WITH_EXPLICIT_CONSENT"}
        return {**payload, "final": "QUARANTINE_CONSENT_REQUIRED"}
''')
(base / "tests" / "test_root_store.py").write_text('''from datetime import datetime, timezone
from validator.root_store import RootStore

CLAIMED_FP = "522E1BF5BE152FA98BED4F01AA441D01092D5A31"

def test_lookup_by_claimed_fingerprint():
    assert RootStore().get_root(CLAIMED_FP)["name"] == "DOD INTEROPERABILITY ROOT CA 2"

def test_recognized_external_not_trusted_by_default():
    d = RootStore().classify_root(CLAIMED_FP)
    assert d.recognized is True
    assert d.trusted is False
    assert d.requires_explicit_consent is True
    assert d.decision == "RECOGNIZED_EXTERNAL_CONSENT_REQUIRED"

def test_metadata_mismatch_quarantines_even_with_consent():
    decision = RootStore().trust_decision(CLAIMED_FP, explicit_consent=True)
    assert decision["final"] == "QUARANTINE_ROOT_METADATA_MISMATCH"
    assert decision["metadata_integrity"]["ok"] is False

def test_unknown_root_quarantines():
    assert RootStore().trust_decision("DEADBEEF")["final"] == "QUARANTINE"

def test_date_window_valid_for_2026():
    assert RootStore().validate_date_window(CLAIMED_FP, datetime(2026, 1, 1, tzinfo=timezone.utc))["ok"] is True

def test_date_window_invalid_after_expiry():
    r = RootStore().validate_date_window(CLAIMED_FP, datetime(2031, 1, 1, tzinfo=timezone.utc))
    assert r["ok"] is False
    assert r["decision"] == "QUARANTINE_ROOT_OUTSIDE_VALIDITY"
''')
(base / "README.md").write_text(f'''# Validator RootStore — DoD Interoperability Root CA 2

Doctrine:

```text
known root != trusted root
recognized root != authorized root
valid chain != approved chain
```

This registers DOD INTEROPERABILITY ROOT CA 2 as `recognized_external`, not trusted by default.

Important validator finding:

```text
claimed SHA-1:  {SUPPLIED_FP}
computed SHA-1 from supplied PEM: {computed_fp}
metadata integrity: {metadata_ok}
```

Because the claimed fingerprint and supplied PEM fingerprint do not match, the validator fails closed:

```text
QUARANTINE_ROOT_METADATA_MISMATCH
```

Run:

```bash
python -m pytest -q
```
''')

result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=str(base), text=True, capture_output=True, timeout=30)
zip_path = Path("/mnt/data/validator-rootstore-dod.zip")
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for p in base.rglob("*"):
        z.write(p, p.relative_to(base.parent))

print(json.dumps({
    "status": "built",
    "file": str(zip_path),
    "claimed_sha1": SUPPLIED_FP,
    "computed_pem_sha1": computed_fp,
    "metadata_integrity_ok": metadata_ok,
    "pytest_returncode": result.returncode,
    "pytest": (result.stdout + result.stderr).strip(),
    "zip_sha3_512": hashlib.sha3_512(zip_path.read_bytes()).hexdigest()
}, indent=2))
