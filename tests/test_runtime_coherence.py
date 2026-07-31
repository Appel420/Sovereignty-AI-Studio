from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_manifest_has_one_canonical_entrypoint() -> None:
    manifest = json.loads((ROOT / "config" / "runtime-coherence.json").read_text())
    canonical = manifest["canonical_runtime"]
    assert canonical["dashboard"] == "SGHv119.html"
    assert canonical["launcher"] == "START_SERVER.sh"
    assert canonical["local_ci"] == "scripts/local-ci.sh"
    assert len(set(canonical.values())) == len(canonical.values())


def test_runtime_manifest_ports_are_symmetric() -> None:
    manifest = json.loads((ROOT / "config" / "runtime-coherence.json").read_text())
    assert manifest["ports"] == {
        "dashboard": 9898,
        "python_bridge": 9897,
        "node_bridge": 9899,
    }


def test_aliases_do_not_become_new_runtime_owners() -> None:
    manifest = json.loads((ROOT / "config" / "runtime-coherence.json").read_text())
    assert manifest["aliases"]["start-all.sh"] == "START_SERVER.sh"
    assert manifest["aliases"]["python3_bridge.py"] == "bridge.py"
    assert manifest["aliases"]["sovereignty_full_server.py"] == "bridge.py"


def test_private_state_and_provider_choice_are_policy_bound() -> None:
    manifest = json.loads((ROOT / "config" / "runtime-coherence.json").read_text())
    policy = manifest["state_policy"]
    assert policy["private_state_is_not_committed"] is True
    assert policy["provider_selection_is_owner_policy"] is True
    assert policy["implicit_fallback_is_disabled"] is True
