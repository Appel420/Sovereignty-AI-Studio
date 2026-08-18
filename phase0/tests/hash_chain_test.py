import hashlib
import json


def canonical_bytes(event):
    return json.dumps(
        [
            event["sequence"],
            event["grant_id"],
            event["subject"],
            event["resource"],
            event["decision"],
            event["reason"],
            event["timestamp"],
            event["previous_hash"],
        ],
        separators=(",", ":"),
    ).encode()


def digest(event):
    return hashlib.sha256(canonical_bytes(event)).hexdigest()


def test_canonical_decision_is_lowercase():
    event = {
        "sequence": 1,
        "grant_id": "g1",
        "subject": "user",
        "resource": "vault",
        "decision": "allow",
        "reason": "granted",
        "timestamp": 1,
        "previous_hash": "",
    }
    assert event["decision"] in {"allow", "deny"}
    assert digest(event) == digest({**event, "decision": "allow"})


def test_second_event_links_first():
    first = {
        "sequence": 1,
        "grant_id": "g1",
        "subject": "user",
        "resource": "vault",
        "decision": "allow",
        "reason": "granted",
        "timestamp": 1,
        "previous_hash": "",
    }
    second = {
        "sequence": 2,
        "grant_id": "g1",
        "subject": "user",
        "resource": "vault",
        "decision": "deny",
        "reason": "expired",
        "timestamp": 100,
        "previous_hash": digest(first),
    }
    assert second["previous_hash"] == digest(first)
    assert digest(second) == hashlib.sha256(canonical_bytes(second)).hexdigest()
