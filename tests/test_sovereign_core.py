import asyncio

from sovereign import init_sovereign, sovereign
import pytest

from sovereign.pqc_signatures import MLDSASigner, PQCUnavailableError


def test_init_sovereign_returns_success():
    result = asyncio.run(init_sovereign())

    assert result["status"] == "success"
    assert result["initialized"] is True


def test_sovereign_api_key_and_rotation():
    api_key = sovereign.derive_api_key("ci-test-service", length=32)

    assert len(api_key) == 64
    assert sovereign.rotate_all("rotation-1")["status"] == "success"


def test_mldsasigner_roundtrip():
    signer = MLDSASigner(algorithm="ML-DSA-87")
    try:
        signature = signer.sign(b"sovereign-ci")
    except PQCUnavailableError:
        with pytest.raises(PQCUnavailableError):
            signer.verify(b"sovereign-ci", b"not-a-signature")
    else:
        assert signer.verify(b"sovereign-ci", signature) is True
