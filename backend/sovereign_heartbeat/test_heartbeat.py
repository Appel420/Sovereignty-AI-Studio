from pathlib import Path

from .heartbeat import SovereignHeartbeat


def test_heartbeat_persists_and_advances(tmp_path: Path) -> None:
    heartbeat = SovereignHeartbeat(tmp_path / "state")

    first = heartbeat.beat(status="ALIVE", repository_head="abc")
    second = heartbeat.beat(status="ALIVE", repository_head="def")
    checkpoint = heartbeat.checkpoint(reason="seven-day-checkpoint", repository_head="def")

    assert first.sequence == 1
    assert second.sequence == 2
    assert checkpoint.sequence == 3
    assert checkpoint.evidence_sequence == 1
    assert heartbeat.load().repository_head == "def"
    assert heartbeat.load().last_checkpoint is not None
    assert len((tmp_path / "state" / "heartbeat.jsonl").read_text().splitlines()) == 3


def test_heartbeat_preserves_prior_events(tmp_path: Path) -> None:
    heartbeat = SovereignHeartbeat(tmp_path / "state")
    heartbeat.beat(status="ALIVE")
    heartbeat.checkpoint(reason="checkpoint")

    records = (tmp_path / "state" / "heartbeat.jsonl").read_text().splitlines()
    assert len(records) == 2
    assert '"type": "heartbeat"' in records[0]
    assert '"type": "checkpoint"' in records[1]
