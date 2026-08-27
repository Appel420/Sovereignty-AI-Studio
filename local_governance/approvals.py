"""Device-local approval queue for governed operations."""
from __future__ import annotations
import hashlib, json, threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
APPROVAL_KINDS=frozenset({"PROCESS","DEPLOYMENT","COMMIT"})

def _now(): return datetime.now(timezone.utc).isoformat()
def _fingerprint(kind, subject, payload): return hashlib.sha256(json.dumps({"kind":kind,"subject":subject,"payload":payload},sort_keys=True,separators=(",",":")).encode()).hexdigest()
class ApprovalStore:
 def __init__(self,path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._lock=threading.RLock(); self._records={}; self._load()
 def _load(self):
  if self.path.exists():
   for line in self.path.read_text("utf-8").splitlines():
    if line.strip():
     r=json.loads(line); self._records[r["approval_id"]]=r
 def _persist(self):
  t=self.path.with_suffix(self.path.suffix+".tmp"); t.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in self._records.values()),encoding="utf-8"); t.replace(self.path)
 def request(self,*,kind,subject,summary,requested_by,payload=None,expires_at=None):
  if kind not in APPROVAL_KINDS: raise ValueError(f"kind must be one of {sorted(APPROVAL_KINDS)}")
  payload=payload or {}; fp=_fingerprint(kind,subject,payload); now=_now()
  with self._lock:
   for r in self._records.values():
    if r["fingerprint"]==fp and r["state"]=="PENDING":
     r["last_notified"]=now; r["notification_count"]+=1; r["audit"].append({"event":"APPROVAL_RENOTIFIED","timestamp":now}); self._persist(); return json.loads(json.dumps(r))
   r={"approval_id":fp[:16],"fingerprint":fp,"kind":kind,"subject":subject,"summary":summary,"requested_by":requested_by,"payload":payload,"state":"PENDING","created_at":now,"last_notified":now,"notification_count":1,"expires_at":expires_at,"audit":[{"event":"APPROVAL_REQUESTED","timestamp":now}]}; self._records[r["approval_id"]]=r; self._persist(); return json.loads(json.dumps(r))
 def list(self,state=None,kind=None):
  with self._lock:
   v=list(self._records.values());
   if state is not None: v=[r for r in v if r["state"]==state]
   if kind is not None: v=[r for r in v if r["kind"]==kind]
   return json.loads(json.dumps(v))
 def decide(self,approval_id,decision,owner):
  if decision not in {"APPROVED","DENIED","EXPIRED","CANCELLED"}: raise ValueError("decision must be APPROVED, DENIED, EXPIRED, or CANCELLED")
  if not owner.strip(): raise ValueError("owner is required")
  with self._lock:
   r=self._records.get(approval_id)
   if r is None: raise KeyError(f"Unknown approval: {approval_id}")
   if r["state"]!="PENDING": raise ValueError(f"Approval is already {r['state']}")
   now=_now(); r.update(state=decision,decided_at=now,decided_by=owner); r["audit"].append({"event":f"APPROVAL_{decision}","timestamp":now,"owner":owner}); self._persist(); return json.loads(json.dumps(r))
