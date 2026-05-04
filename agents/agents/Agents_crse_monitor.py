import os, time, json, requests

audit_file = "/app/audit/audit.jsonl"
os.makedirs(os.path.dirname(audit_file), exist_ok=True)

interval = int(os.environ.get("MONITOR_INTERVAL", 60))
chunk_limit = int(os.environ.get("CHUNK_LIMIT", 50))
max_log_size = int(os.environ.get("MAX_LOG_SIZE", 10*1024*1024))

proposal_chunks = []

# All agents are routed through the gateway on port 9898 (GATEWAY_PORT).
# In Docker each agent is a hostname; all /proposals calls go through the gateway.
_gateway_port = int(os.environ.get("GATEWAY_PORT", 9898))
agent_ports = {
    "judge": _gateway_port,
    "ai_router": _gateway_port,
    "plugin": _gateway_port,
    "platform": _gateway_port,
    "voice": _gateway_port
}

while True:
    for name, port in agent_ports.items():
        try:
            r = requests.get(f"http://{name}:{port}/proposals", timeout=5)
            raw = r.text[:2000000].replace("\n","")  # sanitize
        except:
            raw = "[]"
        proposal_chunks.append(f"{name}: {raw}")
        if len(proposal_chunks) > chunk_limit:
            proposal_chunks = proposal_chunks[-chunk_limit:]
        with open(audit_file, "a") as f:
            f.write(json.dumps({"time": time.time(), "agent": name, "proposal": raw})+"\n")
    # simple critical fail check
    if any("CRITICAL_FAIL" in p for p in proposal_chunks):
        exit(1)
    # rotate log if too big
    if os.path.exists(audit_file) and os.path.getsize(audit_file) > max_log_size:
        os.rename(audit_file, f"{audit_file}.{int(time.time())}.bak")
        open(audit_file, "w").close()
    time.sleep(interval)
