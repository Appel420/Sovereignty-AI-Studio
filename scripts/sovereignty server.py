#!/usr/bin/env python3
"""
sovereignty_server.py
Sovereignty One -- Production API Server
Runs on 127.0.0.1:9897. Zero external calls. All data stays on device.

Start:  python sovereignty_server.py
        uvicorn sovereignty_server:app --host 127.0.0.1 --port 9897 --reload

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Package path ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "sovereignty_one"))

from convergence.engine import ConvergenceEngine
from convergence.config import load_weights
from bridge.wetlab.repair_planner import plan_repair, ORGAN_MODELS
from security.telemetry_signer import TelemetrySigner

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sovereignty One",
    description="Sovereign Distributed Biological Runtime API",
    version="2.2.0",
    docs_url="/docs",
    redoc_url=None,
)

# CORS: localhost only -- no external origins ever
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1",
        "http://localhost",
        "null",              # file:// origin for local HTML
    ],
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons ────────────────────────────────────────────────────────────────
JASPAR_FILE = os.environ.get("JASPAR_FILE")
_engine:    Optional[ConvergenceEngine] = None
_telemetry: Optional[TelemetrySigner]   = None
_ws_clients: List[WebSocket]            = []
_run_history: List[Dict]               = []


def get_engine() -> ConvergenceEngine:
    global _engine
    if _engine is None:
        _engine = ConvergenceEngine(JASPAR_FILE)
    return _engine


def get_telemetry() -> TelemetrySigner:
    global _telemetry
    if _telemetry is None:
        log_path = ROOT / "sovereignty_one" / "telemetry.jsonl"
        _telemetry = TelemetrySigner(str(log_path))
    return _telemetry


async def broadcast(event_type: str, data: dict):
    """Push a signed event to all connected WebSocket clients."""
    telem = get_telemetry()
    event = telem.sign_event(event_type, data)
    msg   = json.dumps({"type": event_type, "data": data,
                         "chain_hash": event["chain_hash"],
                         "ts": event["ts"]}, default=str)
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


# ── Pydantic models ───────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    sequence:  str
    variant:   Optional[Dict[str, Any]] = None
    metadata:  Optional[Dict[str, Any]] = None

class RepairRequest(BaseModel):
    sequence:  str
    variant:   Optional[Dict[str, Any]] = None
    metadata:  Optional[Dict[str, Any]] = None
    organ:     str = "liver"
    disease:   str = "cirrhosis"

class OT2RunRequest(BaseModel):
    protocol_type:    str   = "epigenetic_edit"
    cells_well:       str   = "A1"
    editor_volume_ul: float = 2.0
    guide_volume_ul:  float = 1.0
    simulate:         bool  = True

class SequencerRequest(BaseModel):
    experiment_id:    str   = ""
    platform:         str   = "nanopore"
    reference_genome: Optional[str] = None
    simulate:         bool  = True

class BatchAnalyzeRequest(BaseModel):
    variants: List[Dict[str, Any]]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    telem = get_telemetry()
    return {
        "status":          "ok",
        "version":         "2.2.0-sovereign",
        "engine_ready":    _engine is not None,
        "motifs_loaded":   len(get_engine().motif_engine.motifs),
        "jaspar_source":   "file" if (JASPAR_FILE and Path(JASPAR_FILE).exists()) else "embedded_6",
        "chain_tip":       telem.chain_tip[:16] + "...",
        "events_signed":   telem.event_count,
        "chain_verified":  telem.verify_chain(),
        "ts":              datetime.now(timezone.utc).isoformat(),
    }


@app.get("/config")
async def get_config():
    return {
        "weights":     load_weights(),
        "organs":      list(ORGAN_MODELS.keys()),
        "jaspar_file": JASPAR_FILE,
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.sequence or len(req.sequence) < 10:
        raise HTTPException(400, "Sequence must be at least 10 bp")
    seq = req.sequence.strip().upper().replace(" ", "").replace("\n", "")
    try:
        engine = get_engine()
        cr = engine.analyze(seq, req.variant, req.metadata)
        result = cr.to_dict()
        result["chromatin_detail"] = {
            "state_num":   cr.chromatin.state_num,
            "key_marks":   cr.chromatin.key_marks,
            "gc_content":  cr.chromatin.gc_content,
            "cpg_density": cr.chromatin.cpg_density,
            "confidence":  cr.chromatin.confidence,
        }
        result["motif_detail"] = {
            "disrupted_motifs":  cr.motif.disrupted_motifs,
            "top_motif":         cr.motif.top_motif,
            "strength":          cr.motif.strength,
            "motifs_evaluated":  cr.motif.motifs_evaluated,
            "method":            cr.motif.method,
        }
        result["abc_detail"] = {
            "contact_strength": cr.abc.contact_strength,
            "activity":         cr.abc.activity,
            "method":           cr.abc.method,
        }
        result["conservation_detail"] = {
            "score":  cr.conservation.conservation_score,
            "method": cr.conservation.method,
        }
        _run_history.append({"type": "analyze", "ts": time.time(), "result": result})
        await broadcast("analyze_complete", result)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/plan-repair")
async def plan_repair_endpoint(req: RepairRequest):
    if not req.sequence or len(req.sequence) < 10:
        raise HTTPException(400, "Sequence too short")
    seq = req.sequence.strip().upper().replace(" ", "").replace("\n", "")
    try:
        engine = get_engine()
        cr     = engine.analyze(seq, req.variant, req.metadata)
        hyp    = plan_repair(cr, req.organ, req.disease)
        result = {
            "convergence_score":  cr.convergence_score,
            "tier":               cr.tier,
            "repair_hypothesis":  hyp.to_dict(),
        }
        await broadcast("repair_planned", result)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/run-ot2")
async def run_ot2(req: OT2RunRequest):
    try:
        from lab.hardware.opentrons.ot2_adapter import OT2Adapter
        ot2 = OT2Adapter(simulate=req.simulate)
        if req.protocol_type == "gsis":
            protocol = ot2.build_gsis_assay_protocol()
        else:
            protocol = ot2.build_epigenetic_edit_protocol(
                cells_well       = req.cells_well,
                editor_volume_ul = req.editor_volume_ul,
                guide_volume_ul  = req.guide_volume_ul,
            )
        run_id  = ot2.run(protocol)
        status  = ot2.poll_run(run_id)
        telemetry = ot2.get_telemetry(run_id)
        result  = {
            "run_id":    run_id,
            "status":    status.get("status", "complete"),
            "steps":     len(protocol.steps),
            "protocol":  req.protocol_type,
            "simulated": req.simulate,
            "live_hardware": not req.simulate and ot2._check_connection(),
        }
        get_telemetry().sign_event("ot2_run", result)
        await broadcast("ot2_complete", result)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/run-sequencer")
async def run_sequencer(req: SequencerRequest):
    try:
        from lab.hardware.sequencing.sequencer_adapter import SequencerAdapter
        seq = SequencerAdapter(simulate=req.simulate, platform=req.platform)
        result_obj = seq.full_run(
            experiment_id    = req.experiment_id or f"sov1_{uuid.uuid4().hex[:8]}",
            reference        = req.reference_genome,
        )
        result = {
            "run_id":        result_obj.run_id,
            "total_reads":   result_obj.total_reads,
            "q30_fraction":  result_obj.q30_fraction,
            "median_length": result_obj.median_length,
            "coverage_mean": result_obj.coverage_mean,
            "on_target_pct": result_obj.on_target_pct,
            "variants_vcf":  result_obj.variants_vcf,
            "success":       result_obj.success,
            "simulated":     req.simulate,
        }
        get_telemetry().sign_event("sequencer_run", result)
        await broadcast("sequencing_complete", result)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/batch-analyze")
async def batch_analyze(req: BatchAnalyzeRequest):
    engine = get_engine()
    results = []
    for item in req.variants:
        try:
            seq = item.get("sequence", "").strip().upper()
            cr  = engine.analyze(seq, item.get("variant"), item.get("metadata"))
            results.append({"ok": True, "result": cr.to_dict()})
        except Exception as e:
            results.append({"ok": False, "error": str(e)})
    return {"count": len(results), "results": results}


@app.get("/telemetry")
async def get_telemetry_log(n: int = 50):
    log_path = ROOT / "sovereignty_one" / "telemetry.jsonl"
    events = []
    if log_path.exists():
        lines = log_path.read_bytes().splitlines()
        for line in lines[-n:]:
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    telem = get_telemetry()
    return {
        "events":        events,
        "total":         len(events),
        "chain_tip":     telem.chain_tip,
        "chain_verified": telem.verify_chain(),
        "events_signed": telem.event_count,
    }


@app.get("/history")
async def get_history(n: int = 20):
    return {"runs": _run_history[-n:], "total": len(_run_history)}


@app.get("/hardware-status")
async def hardware_status():
    """Check what hardware is actually reachable -- no simulation, real sockets."""
    import socket
    def reachable(host: str, port: int) -> bool:
        try:
            s = socket.create_connection((host, port), timeout=1.5)
            s.close()
            return True
        except Exception:
            return False

    ot2_host     = os.environ.get("OT2_HOST", "10.0.0.10")
    seq_host     = os.environ.get("SEQUENCER_HOST", "10.0.0.30")
    hamilton_host= os.environ.get("HAMILTON_HOST", "10.0.0.20")

    return {
        "ot2": {
            "host":        ot2_host,
            "port":        int(os.environ.get("OT2_PORT", 31950)),
            "reachable":   reachable(ot2_host, int(os.environ.get("OT2_PORT", 31950))),
        },
        "sequencer": {
            "host":      seq_host,
            "port":      8000,
            "reachable": reachable(seq_host, 8000),
        },
        "hamilton": {
            "host":      hamilton_host,
            "port":      int(os.environ.get("HAMILTON_PORT", 8080)),
            "reachable": reachable(hamilton_host, int(os.environ.get("HAMILTON_PORT", 8080))),
        },
        "ts": datetime.now(timezone.utc).isoformat(),
    }


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    if len(_ws_clients) >= 20:
        await ws.close(code=1013, reason="Max connections reached")
        return
    await ws.accept()
    _ws_clients.append(ws)
    try:
        # Send current status on connect
        telem = get_telemetry()
        await ws.send_text(json.dumps({
            "type": "connected",
            "data": {
                "version":       "2.2.0-sovereign",
                "chain_tip":     telem.chain_tip[:16] + "...",
                "events_signed": telem.event_count,
            }
        }))
        while True:
            msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
            # Echo back signed
            event = get_telemetry().sign_event("ws_message", {"raw": msg[:200]})
            await ws.send_text(json.dumps({
                "type": "ack",
                "chain_hash": event["chain_hash"],
            }))
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    # Warm up engine so first request is fast
    get_engine()
    get_telemetry().sign_event("server_start", {
        "version": "2.2.0-sovereign",
        "jaspar":  JASPAR_FILE or "embedded",
        "pid":     os.getpid(),
    })
    print("\n[Sovereignty One] Server ready on http://127.0.0.1:9897")
    print("[Sovereignty One] Open sovereignty_one_platform.html in your browser")
    print("[Sovereignty One] Zero external calls -- all data stays on device\n")


if __name__ == "__main__":
    uvicorn.run(
        "sovereignty_server:app",
        host    = "127.0.0.1",
        port    = 9897,
        reload  = False,
        workers = 1,
    )
