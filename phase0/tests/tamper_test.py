import hashlib
import json


def canonical(event):
    return json.dumps(
        [event[k] for k in (
            "sequence", "grant_id", "subject", "resource", "decision",
            "reason", "timestamp", "previous_hash"
        )],
        separators=(",", ":"),
    ).encode()


def verify_chain(events):
    previous = ""
    for index, event in enumerate(events, start=1):
        expected = hashlib.sha256(canonical(event)).hexdigest()
        if event["sequence"] != index:
            return False
        if event["previous_hash"] != previous:
            return False
        if event["hash"] != expected:
            return False
        previous = event["hash"]
    return True


def test_mutation_is_detected():
    first = {
        "sequence": 1, "grant_id": "g1", "subject": "user", "resource": "vault",
        "decision": "allow", "reason": "granted", "timestamp": 1, "previous_hash": "",
    }
    first["hash"] = hashlib.sha256(canonical(first)).hexdigest()
    second = {
        "sequence": 2, "grant_id": "g1", "subject": "user", "resource": "vault",
        "decision": "deny", "reason": "expired", "timestamp": 100,
        "previous_hash": first["hash"],
    }
    second["hash"] = hashlib.sha256(canonical(second)).hexdigest()
    events = [first, second]
    assert verify_chain(events)
    events[1]["reason"] = "tampered"
    assert not verify_chain(events)
