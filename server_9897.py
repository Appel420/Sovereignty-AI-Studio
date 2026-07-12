#!/usr/bin/env python3
"""
SuperGrok 4.2 CI/CD Bridge — Port 9897
Run: pip install fastapi uvicorn websockets && python server_9897.py
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import datetime
import json
import uuid
from pathlib import Path
import uvicorn
from typing import List, Optional

app = FastAPI(title="SuperGrok CI/CD Bridge", version="4.2.0")

app.add_middleware(CORSMiddleware,
    allow_origins=["http://127.0.0.1:9898", "http://localhost:9898"],
    allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])

# Connected WebSocket clients
class ConnectionManager:
    def __init__(self): self.active: List[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept(); self.active.append(ws)
    def disconnect(self, ws: WebSocket):
        if ws in self.active: self.active.remove(ws)
    async def broadcast(self, msg: dict):
        disconnected = []
        for ws in self.active:
            try: await ws.send_json(msg)
            except: disconnected.append(ws)
        for ws in disconnected: self.disconnect(ws)

manager = ConnectionManager()
build_logs: List[dict] = []
start_time = datetime.datetime.now()
REPOSITORY_ROOT = Path(__file__).resolve().parent
build_running = False

class RunRequest(BaseModel):
    user: str = ""
    role: str = ""
    ts: str = ""
    trigger: str = "manual"

class WebhookPayload(BaseModel):
    type: str
    data: Optional[dict] = None

@app.get("/health")
async def health():
    uptime = (datetime.datetime.now() - start_time).seconds
    return {
        "status": "ok", "version": "4.2.0",
        "port": 9897, "uptime_seconds": uptime,
        "connections": len(manager.active),
        "ts": datetime.datetime.now().isoformat()
    }

@app.get("/status")
async def status():
    return {
        "status": "running", "build_count": len(build_logs),
        "ws_clients": len(manager.active),
        "ts": datetime.datetime.now().isoformat()
    }

@app.post("/build")
async def build(req: RunRequest, is_test: bool = False):
    global build_running
    if build_running:
        raise HTTPException(status_code=409, detail="A local CI run is already in progress.")

    build_running = True
    entry = {
        "id": f"BUILD-{uuid.uuid4().hex[:8].upper()}",
        "triggered_by": req.user, "role": req.role,
        "ts": datetime.datetime.now().isoformat(), "status": "started"
    }
    build_logs.append(entry)
    await manager.broadcast({"type":"log","level":"info","msg":f"Build started by {req.user} ({req.role})"})

    async def run_build():
        global build_running
        try:
            process = await asyncio.create_subprocess_exec(
                "bash", "scripts/local-ci.sh",
                cwd=REPOSITORY_ROOT,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert process.stdout is not None
            async for line in process.stdout:
                await manager.broadcast({
                    "type": "log",
                    "level": "info",
                    "msg": line.decode(errors="replace").rstrip(),
                })
            return_code = await process.wait()
            entry["status"] = "success" if return_code == 0 else "failed"
            entry["exit_code"] = return_code
            await manager.broadcast({
                "type": "build_complete",
                "status": entry["status"],
                "id": entry["id"],
                "exit_code": return_code,
            })
            if is_test:
                await manager.broadcast({
                    "type": "test_result",
                    "passed": 1 if return_code == 0 else 0,
                    "failed": 0 if return_code == 0 else 1,
                })
        finally:
            build_running = False
    asyncio.create_task(run_build())
    return {"triggered": True, "id": entry["id"], "by": req.user}

@app.post("/test")
async def run_tests(req: RunRequest = None):
    await manager.broadcast({"type":"log","level":"info","msg":"Test suite started"})
    return await build(req or RunRequest(trigger="test"), is_test=True)

@app.post("/run")
async def run_cmd(req: RunRequest):
    return {"executed": False, "reason": "Arbitrary commands are disabled. Use /build for local CI."}

@app.get("/logs")
async def get_logs(limit: int = 50):
    return {"logs": build_logs[-limit:], "total": len(build_logs)}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    await ws.send_json({
        "type": "connected",
        "msg": f"SuperGrok Bridge 4.2 — {len(manager.active)} client(s) connected",
        "ts": datetime.datetime.now().isoformat()
    })
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "build":
                    req = RunRequest(**{k:v for k,v in msg.items() if k in RunRequest.model_fields})
                    await build(req)
                elif msg.get("type") == "ping":
                    await ws.send_json({"type":"pong","ts":datetime.datetime.now().isoformat()})
                else:
                    await manager.broadcast({"type":"log","level":"info","msg":f"WS: {str(msg)[:1000]}"})
            except json.JSONDecodeError:
                await ws.send_json({"type":"error","msg":"Invalid JSON"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast({"type":"log","level":"warn","msg":f"Client disconnected — {len(manager.active)} remaining"})

if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  SuperGrok 4.2 CI/CD Bridge — Port 9897 ║")
    print("║  WebSocket: ws://localhost:9897/ws       ║")
    print("║  Health:    http://localhost:9897/health ║")
    print("╚══════════════════════════════════════════╝")
    uvicorn.run(app, host="127.0.0.1", port=9897, log_level="info")
