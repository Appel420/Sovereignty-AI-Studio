import asyncio

from sovereign import init_sovereign, sovereign
from sovereign.pqc_signatures import MLDSASigner


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
    message = b"sovereign-ci"
    signature = signer.sign(message)

    assert signer.verify(message, signature) is True
