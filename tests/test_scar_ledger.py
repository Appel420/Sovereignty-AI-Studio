from __future__ import annotations

from sovereign.scar.ledger import EventClass, SCARActor, SCARLedger


class Signed:
    def __init__(self, signature: bytes) -> None:
        self.signature = signature


class TestRoot:
    def sign(self, payload: bytes) -> Signed:
        # Deterministic test signer; production injects the real root-of-trust.
        return Signed(payload[:32])


def test_route_trace_and_event_class_are_signed_and_verifiable() -> None:
    ledger = SCARLedger("device:test", TestRoot())
    event = ledger.append_event(
        "ROUTE_DECISION",
        actor=SCARActor.DEVICE,
        event_class=EventClass.ROUTING,
        capability_id="route.local",
        route_trace={"trace_id": "t1", "selected_provider": "local"},
        classification_level=1,
        metadata={"reason": "policy-approved"},
    )

    assert event.event_class is EventClass.ROUTING
    assert event.route_trace["trace_id"] == "t1"
    assert event.classification_level == 1
    assert event.signing_document()["event_class"] == "routing"
    assert event.signing_document()["route_trace"]["selected_provider"] == "local"
    assert ledger.verify_chain()


def test_provider_requires_capability_provenance() -> None:
    ledger = SCARLedger("device:test", TestRoot())
    try:
        ledger.append_event(
            "PROVIDER_CALL",
            actor=SCARActor.PROVIDER,
            event_class=EventClass.AI_REQUEST,
        )
    except Exception as exc:
        assert "capability provenance" in str(exc)
    else:
        raise AssertionError("provider event without capability must fail closed")


def test_classification_level_is_bounded() -> None:
    ledger = SCARLedger("device:test", TestRoot())
    for invalid in (-1, 5):
        try:
            ledger.append_event(
                "TEST",
                actor=SCARActor.DEVICE,
                event_class=EventClass.SYSTEM,
                classification_level=invalid,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("invalid classification level was accepted")
