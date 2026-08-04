"""Regression tests for the SCAR mail-transport scope boundary."""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit-external-integrations.py"
SPEC = importlib.util.spec_from_file_location("audit_external_integrations", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_mail_transport_is_out_of_scar_scope() -> None:
    result = MODULE._mail_transport_scope(
        "example.org MX mail.google.com; SMTP relay; SPF record", "docs/example.md"
    )
    assert result == "OUT_OF_SCAR_SCOPE"


def test_scope_addendum_is_documented() -> None:
    result = MODULE._mail_transport_scope(
        "SCAR Scope Addendum — Mail-Transport Layer Exclusion",
        "docs/compliance/SCAR_SCOPE_ADDENDUM_MAIL_TRANSPORT.md",
    )
    assert result == "DOCUMENTED_SCOPE_BOUNDARY"
