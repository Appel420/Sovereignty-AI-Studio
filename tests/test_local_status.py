"""Focused tests for local dashboard status (offline / M4 / OAuth surface)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.local_dashboard_status import local_status  # noqa: E402
from bridge.serve_dashboard import _local_status  # noqa: E402


def test_local_status_offline_contract() -> None:
    data = local_status()
    assert data["mode"] == "offline"
    assert data["network_access"] is False
    assert "m4_neural" in data
    m4 = data["m4_neural"]
    assert m4["tops"] == 38
    assert m4["memory"] == "unified"
    assert m4["path"] == "docs/apple_m4_neural.md"


def test_serve_dashboard_local_status_route_payload() -> None:
    data = _local_status()
    assert data.get("mode") == "offline"
    assert "m4_neural" in data
    assert data["m4_neural"].get("tops") == 38
