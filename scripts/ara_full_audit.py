#!/usr/bin/env python3
"""Fail-closed ARA repository/ruleset audit.

Audit only. Never changes rulesets, refs, files, credentials, or permissions.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, urllib.error, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "Appel420/Sovereignty-AI-Studio")
BRANCH = os.environ.get("ARA_CANONICAL_BRANCH", "Collaboration")
RULESET = os.environ.get("ARA_RULESET_NAME", "Ara")
REPORT = ROOT / "automation/reports/ara_full_audit.json"
IGNORE = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}


def rel(p: Path) -> str: return p.relative_to(ROOT).as_posix()

def git(*args: str) -> str:
    try: return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception: return ""

def files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and not any(x in IGNORE for x in p.parts))

def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def api(path: str, token: str):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept":"application/vnd.github+json", "Authorization":f"Bearer {token}", "X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)

def main() -> int:
    fs = files(); buckets = defaultdict(list)
    for p in fs: buckets[digest(p)].append(rel(p))
    dupes = [v for v in buckets.values() if len(v) > 1]
    nested = [rel(p.parent) for p in ROOT.rglob(".git") if p != ROOT / ".git"]
    snapshots = [rel(p) for p in fs if "/Sovereignty-AI-Studio-main/" in rel(p) and rel(p).startswith("external/")]
    templates = []
    for p in fs:
        if p.name.lower() == "dependabot.yaml" and "example.com" in p.read_text(errors="ignore"): templates.append(rel(p))
        if p.name in {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}: templates.append(rel(p))
    local = {"branch":git("branch","--show-current"),"head":git("rev-parse","HEAD"),"files_scanned":len(fs),"duplicate_groups":dupes,"nested_git_repositories":nested,"nested_studio_snapshot_paths":snapshots,"credential_or_template_risks":templates,"status":git("status","--porcelain=v1").splitlines()}
    remote = {"checked":False}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        try:
            rs = api(f"/repos/{REPO}/rulesets", token)
            matches = [r for r in rs if r.get("name","").casefold() == RULESET.casefold()]
            remote = {"checked":True,"matches":[api(f"/repos/{REPO}/rulesets/{r['id']}",token) for r in matches]}
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
            remote = {"checked":False,"error":str(e)}
    findings=[]
    if nested: findings.append({"severity":"HIGH","code":"NESTED_REPOSITORY"})
    if snapshots: findings.append({"severity":"HIGH","code":"NESTED_STUDIO_SNAPSHOT"})
    if templates: findings.append({"severity":"HIGH","code":"CREDENTIAL_OR_TEMPLATE_RISK"})
    if dupes: findings.append({"severity":"MEDIUM","code":"DUPLICATE_CONTENT","groups":len(dupes)})
    if remote.get("checked"):
        matches=remote.get("matches",[])
        if not matches: findings.append({"severity":"CRITICAL","code":"ARA_RULESET_MISSING"})
        for r in matches:
            if r.get("enforcement") != "active": findings.append({"severity":"CRITICAL","code":"ARA_RULESET_DISABLED"})
            refs=((r.get("conditions") or {}).get("ref_name") or {})
            if refs.get("include") and not any(BRANCH in x for x in refs["include"]): findings.append({"severity":"HIGH","code":"CANONICAL_BRANCH_NOT_COVERED"})
            for b in r.get("bypass_actors") or []:
                if b.get("bypass_mode") == "always" and b.get("actor_id") is None: findings.append({"severity":"CRITICAL","code":"UNSCOPED_BYPASS"})
    result={"repository":REPO,"canonical_branch":BRANCH,"ruleset":RULESET,"local":local,"remote_ruleset":remote,"findings":findings,"fail_closed":True}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"findings":len(findings),"report":str(REPORT)},indent=2))
    return 1 if any(x["severity"] in {"CRITICAL","HIGH"} for x in findings) else 0

if __name__ == "__main__": raise SystemExit(main())
