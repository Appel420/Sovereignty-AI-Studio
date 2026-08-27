"""Device-local deduplicated issue suggestions."""
from __future__ import annotations
import hashlib,json,re,threading
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

def _now(): return datetime.now(timezone.utc).isoformat()
def _normalize(v):
 t=str(v or "").strip().lower(); return re.sub(r"0x[0-9a-f]+|[0-9a-f]{8,}","<id>",re.sub(r"\s+"," ",t))
def suggestion_fingerprint(*,category,reason,source="",component="",target="",mode=""):
 return hashlib.sha256("|".join(_normalize(v) for v in (category,reason,source,component,target,mode)).encode()).hexdigest()
class IssueSuggestionStore:
 def __init__(self,path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._lock=threading.RLock(); self._records={}; self._load()
 def _load(self):
  if self.path.exists():
   for line in self.path.read_text("utf-8").splitlines():
    if line.strip():
     r=json.loads(line); self._records[r["fingerprint"]]=r
 def _persist(self):
  t=self.path.with_suffix(self.path.suffix+".tmp"); t.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in self._records.values()),encoding="utf-8"); t.replace(self.path)
 def observe(self,*,category,reason,title,evidence,source="",component="",target="",mode="offline",recommended_action="Review the evidence and choose an owner decision."):
  fp=suggestion_fingerprint(category=category,reason=reason,source=source,component=component,target=target,mode=mode); now=_now()
  with self._lock:
   r=self._records.get(fp)
   if r is None:
    r={"suggestion_id":fp[:16],"fingerprint":fp,"state":"PROPOSED","category":category,"title":title,"reason":reason,"evidence":[evidence],"source":source,"component":component,"target":target,"mode":mode,"recommended_action":recommended_action,"first_seen":now,"last_seen":now,"occurrences":1,"owner_decision":"PENDING","audit":[{"event":"ISSUE_SUGGESTION_PROPOSED","timestamp":now,"owner_action":False}]}; self._records[fp]=r
   else:
    r["last_seen"]=now; r["occurrences"]+=1
    if evidence not in r["evidence"]: r["evidence"].append(evidence)
    r["audit"].append({"event":"ISSUE_SUGGESTION_DEDUPED","timestamp":now,"owner_action":False})
   self._persist(); return json.loads(json.dumps(r))
 def list(self,state=None):
  v=list(self._records.values()) if state is None else [r for r in self._records.values() if r["state"]==state]; return json.loads(json.dumps(v))
 def decide(self,suggestion_id,decision):
  if decision not in {"ACCEPTED","DECLINED","DEFERRED","RESOLVED"}: raise ValueError("decision must be ACCEPTED, DECLINED, DEFERRED, or RESOLVED")
  with self._lock:
   r=next((x for x in self._records.values() if x["suggestion_id"]==suggestion_id),None)
   if r is None: raise KeyError(f"Unknown issue suggestion: {suggestion_id}")
   r["state"]=decision; r["owner_decision"]=decision; r["audit"].append({"event":f"ISSUE_SUGGESTION_{decision}","timestamp":_now(),"owner_action":True}); self._persist(); return json.loads(json.dumps(r))
