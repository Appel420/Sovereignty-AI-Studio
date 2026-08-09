"""Contract checks for explicit non-production attestation fallbacks."""
from __future__ import annotations

from core.security.arm_trustzone import ArmTrustZoneAttester
from core.security.sgx_dcap_attestation import SGXDCAPAttester
from core.security.tpm_attestation import TPMAttester


def test_tpm_fallback_is_explicitly_unverified() -> None:
    result = TPMAttester().attest()
    assert result.verified is False
    assert result.details["status"] == "not_implemented"
    assert TPMAttester().status()["status"] == "unavailable"


def test_sgx_fallback_is_explicitly_unverified() -> None:
    result = SGXDCAPAttester().attest()
    assert result.verified is False
    assert result.details["status"] == "not_implemented"
    assert SGXDCAPAttester().status()["status"] == "unavailable"


def test_trustzone_fallback_is_explicitly_unverified() -> None:
    result = ArmTrustZoneAttester().attest()
    assert result.verified is False
    assert result.details["status"] == "not_implemented"
    assert ArmTrustZoneAttester().status()["status"] == "unavailable"
