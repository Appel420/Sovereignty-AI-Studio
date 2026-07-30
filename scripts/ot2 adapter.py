"""
lab/hardware/opentrons/ot2_adapter.py

Real Opentrons OT-2 adapter.
Connects to a live OT-2 robot via the Opentrons HTTP API (port 31950).
Falls back to a simulation mode when the robot is unreachable so the
rest of the pipeline still runs and logs correctly.

OT-2 HTTP API docs: https://docs.opentrons.com/v2/new_protocol_api.html
                    http://{OT2_HOST}:31950/openapi.json

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error


OT2_HOST  = os.environ.get("OT2_HOST", "10.0.0.10")
OT2_PORT  = int(os.environ.get("OT2_PORT", "31950"))
OT2_BASE  = f"http://{OT2_HOST}:{OT2_PORT}"
TIMEOUT_S = 10


@dataclass
class OT2Step:
    action:      str                   # aspirate | dispense | mix | move
    labware:     str                   # e.g. "corning_96_wellplate"
    well:        str                   # e.g. "A1"
    volume_ul:   float = 0.0
    pipette:     str   = "p300_single_gen2"
    params:      Dict  = field(default_factory=dict)


@dataclass
class OT2Protocol:
    protocol_id:   str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    steps:         List[OT2Step] = field(default_factory=list)
    metadata:      Dict = field(default_factory=dict)
    simulate_only: bool = False


class OT2Adapter:
    """
    Interface to a physical Opentrons OT-2.
    All operations are logged to the sovereign telemetry bus.

    Usage:
        adapter = OT2Adapter()
        protocol = adapter.build_epigenetic_edit_protocol(
            cells_well="A1",
            editor_volume_ul=2.0,
            guide_volume_ul=1.0
        )
        run_id = adapter.run(protocol)
        status = adapter.poll_run(run_id)
    """

    def __init__(self, simulate: bool = False):
        self.simulate = simulate or not self._check_connection()
        mode = "SIMULATION" if self.simulate else "LIVE"
        print(f"[OT2Adapter] Mode: {mode} | Host: {OT2_BASE}")

    def _check_connection(self) -> bool:
        try:
            r = urllib.request.urlopen(f"{OT2_BASE}/health", timeout=3)
            return r.status == 200
        except Exception:
            return False

    def _post(self, path: str, body: dict) -> dict:
        if self.simulate:
            return {"id": str(uuid.uuid4()), "status": "simulated", "data": body}
        url = f"{OT2_BASE}{path}"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"OT2 HTTP {e.code} on {path}: {e.read()}")

    def _get(self, path: str) -> dict:
        if self.simulate:
            return {"status": "finished", "data": {}}
        try:
            with urllib.request.urlopen(f"{OT2_BASE}{path}", timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read())
        except Exception as e:
            raise RuntimeError(f"OT2 GET {path} failed: {e}")

    # ── Protocol builders ────────────────────────────────────────────────────

    def build_epigenetic_edit_protocol(
        self,
        cells_well:        str   = "A1",
        editor_volume_ul:  float = 2.0,
        guide_volume_ul:   float = 1.0,
        mix_cycles:        int   = 3,
        plate_type:        str   = "corning_96_wellplate_360ul_flat",
    ) -> OT2Protocol:
        """
        Build an OT-2 protocol for transfecting epigenetic editor + guide RNA
        into cells in a 96-well plate.

        Workflow:
          1. Aspirate editor mRNA from tube rack
          2. Aspirate guide RNA
          3. Mix in well
          4. Dispense into cell-containing well
          5. Mix to ensure distribution
        """
        steps = [
            OT2Step("aspirate", "opentrons_24_tuberack_generic_2ml_screwcap",
                    "A1", editor_volume_ul, "p300_single_gen2",
                    {"source_well": "A1", "comment": "Editor mRNA"}),
            OT2Step("aspirate", "opentrons_24_tuberack_generic_2ml_screwcap",
                    "A2", guide_volume_ul, "p300_single_gen2",
                    {"source_well": "A2", "comment": "Guide RNA"}),
            OT2Step("mix",      plate_type, cells_well,
                    (editor_volume_ul + guide_volume_ul) * 0.8, "p300_single_gen2",
                    {"repetitions": mix_cycles}),
            OT2Step("dispense", plate_type, cells_well,
                    editor_volume_ul + guide_volume_ul, "p300_single_gen2", {}),
            OT2Step("mix",      plate_type, cells_well,
                    (editor_volume_ul + guide_volume_ul) * 0.8, "p300_single_gen2",
                    {"repetitions": mix_cycles, "comment": "Final mixing"}),
        ]
        return OT2Protocol(
            steps    = steps,
            metadata = {
                "protocol_name": "epigenetic_edit",
                "editor_vol":    editor_volume_ul,
                "guide_vol":     guide_volume_ul,
                "cells_well":    cells_well,
            }
        )

    def build_gsis_assay_protocol(
        self,
        well_range:      List[str] = None,
        low_glucose_mM:  float     = 2.8,
        high_glucose_mM: float     = 16.7,
    ) -> OT2Protocol:
        """
        Glucose-stimulated insulin secretion (GSIS) protocol.
        Adds low-glucose KRB, incubates, aspirates supernatant (low),
        then switches to high-glucose KRB for the stimulation phase.
        Aspirates to ELISA plate for insulin measurement.
        """
        wells = well_range or [f"{r}{c}" for r in "ABCD" for c in "12345678"]
        steps = []
        for well in wells:
            steps.append(OT2Step(
                "dispense", "corning_96_wellplate_360ul_flat",
                well, 100.0, "p300_single_gen2",
                {"reagent": f"KRB_{low_glucose_mM}mM_glucose", "comment": "Wash / basal"}
            ))
        for well in wells:
            steps.append(OT2Step(
                "aspirate", "corning_96_wellplate_360ul_flat",
                well, 90.0, "p300_single_gen2",
                {"comment": "Remove basal media"}
            ))
            steps.append(OT2Step(
                "dispense", "corning_96_wellplate_360ul_flat",
                well, 100.0, "p300_single_gen2",
                {"reagent": f"KRB_{high_glucose_mM}mM_glucose", "comment": "Stimulation"}
            ))
        return OT2Protocol(
            steps    = steps,
            metadata = {
                "protocol_name":    "GSIS",
                "low_glucose_mM":   low_glucose_mM,
                "high_glucose_mM":  high_glucose_mM,
                "wells":            wells,
            }
        )

    # ── Execution ────────────────────────────────────────────────────────────

    def run(self, protocol: OT2Protocol) -> str:
        """
        Upload and start a protocol run on the OT-2.
        Returns run_id for polling.
        """
        if self.simulate:
            run_id = f"sim_{protocol.protocol_id}"
            print(f"[OT2Adapter] Simulating run {run_id} ({len(protocol.steps)} steps)")
            return run_id

        # Upload protocol as JSON (in production this would be a .py file uploaded)
        payload = {
            "data": {
                "protocolKind": "json",
                "metadata": protocol.metadata,
                "schemaVersion": 7,
                "commands": [
                    {
                        "commandType": s.action,
                        "params": {
                            "pipetteId": s.pipette,
                            "labwareId": s.labware,
                            "wellName":  s.well,
                            "volume":    s.volume_ul,
                            **s.params,
                        }
                    }
                    for s in protocol.steps
                ]
            }
        }
        upload_resp = self._post("/protocols", payload)
        protocol_server_id = upload_resp.get("data", {}).get("id", "")

        run_resp = self._post("/runs", {"data": {"protocolId": protocol_server_id}})
        run_id   = run_resp.get("data", {}).get("id", "")

        # Start the run
        self._post(f"/runs/{run_id}/actions", {"data": {"actionType": "play"}})
        print(f"[OT2Adapter] Run started: {run_id}")
        return run_id

    def poll_run(self, run_id: str, timeout_s: int = 3600) -> dict:
        """Poll run status until finished or failed. Returns final run record."""
        if self.simulate:
            time.sleep(0.1)
            return {"status": "succeeded", "run_id": run_id, "simulated": True}

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            data = self._get(f"/runs/{run_id}")
            status = data.get("data", {}).get("status", "")
            print(f"[OT2Adapter] Run {run_id}: {status}")
            if status in ("succeeded", "failed", "stopped"):
                return data.get("data", {})
            time.sleep(10)
        raise TimeoutError(f"OT-2 run {run_id} did not finish in {timeout_s}s")

    def get_telemetry(self, run_id: str) -> List[dict]:
        """Return all commands/telemetry for a completed run."""
        if self.simulate:
            return [{"type": "simulated", "run_id": run_id}]
        data = self._get(f"/runs/{run_id}/commands")
        return data.get("data", [])
