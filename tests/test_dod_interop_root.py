"""Tests for the fail-closed DOD interoperability-root trust gate."""

from sovereignty_ai.validator.dod_interop_root import ROOT, Store, pem_sha1


def test_pem_fingerprint_mismatch_is_detected():
    assert pem_sha1(ROOT["pem"]) != ROOT["fingerprint_sha1_claimed"]


def test_recognized_root_requires_explicit_consent():
    result = Store().decision(ROOT["id"])

    assert result["recognized"] is True
    assert result["trusted"] is False
    assert result["final"] == "QUARANTINE_ROOT_METADATA_MISMATCH"


def test_explicit_consent_allows_only_valid_verified_root():
    store = Store()
    root = store.roots[ROOT["id"]]
    root["fingerprint_sha1_claimed"] = root["fingerprint_sha1_pem_computed"]
    root["metadata_integrity_ok"] = True

    result = store.decision(root["fingerprint_sha1_claimed"], consent=True)

    assert result["metadata_integrity"]["ok"] is True
    assert result["date_status"]["ok"] is True
    assert result["final"] == "ALLOW_WITH_EXPLICIT_CONSENT"


def test_metadata_mismatch_quarantines_despite_consent():
    store = Store()
    store.roots[ROOT["id"]]["metadata_integrity_ok"] = False

    result = store.decision(ROOT["id"], consent=True)

    assert result["final"] == "QUARANTINE_ROOT_METADATA_MISMATCH"


def test_unknown_root_is_quarantined():
    result = Store().decision("unregistered-root", consent=True)

    assert result["recognized"] is False
    assert result["final"] == "QUARANTINE"


def test_public_roots_never_exposes_pem():
    roots = Store().public_roots()

    assert len(roots) == 1
    assert "pem" not in roots[0]
