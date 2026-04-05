from pathlib import Path
import zipfile, shutil, os, textwrap, json, datetime

src_zip = Path('/mnt/data/Sovereignty-AI-Studio-main-fixed.zip')
workdir = Path('/mnt/data/adventure_repo')
out_zip = Path('/mnt/data/Sovereignty-AI-Studio-main-adventure-logged.zip')

if workdir.exists():
    shutil.rmtree(workdir)
workdir.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(src_zip, 'r') as zf:
    zf.extractall(workdir)

# find root extracted folder
entries = [p for p in workdir.iterdir()]
root = entries[0] if len(entries)==1 and entries[0].is_dir() else workdir

log_path = root / 'AGENT_ADVENTURE_LOG.md'
timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
content = f"""# Agent Adventure Log

Authorized by: `appel420`
Logged by: `GPT`
Timestamp: `{timestamp}`

## Mission
Continue cleanup work in a reversible, auditable way and log what changed.

## Changes already completed
- Reorganized misplaced root files into cleaner repo locations.
- Created missing directories used by the maintenance layout.
- Upgraded `ai_agents/repo_maintenance_agent.py` with:
  - repo root auto-detection
  - stronger allowlist awareness
  - `--fix`
  - `--dry-run`
  - `--json`
- Added a repository maintenance report.

## Files moved in prior cleanup
- `Authorized_Only.html` -> `docs/html/Authorized_Only.html`
- `SGHv119.html` -> `docs/html/SGHv119.html`
- `Enterprise_Audio_Platform.swift` -> `docs/planning/Enterprise_Audio_Platform.md`
- `WebSocket.swift` -> `docs/planning/WebSocket_Bridge_Notes.md`
- `Nodejs25changeLog_Node.js` -> `docs/planning/Nodejs25changeLog_Node.md`
- `Uvicorn.run` -> `scripts/python/uvicorn_9898.py`
- `Sanatizer.js` -> `scripts/javascript/sanitizer.js`
- `sg_change_log.py` -> `scripts/python/sg_change_log.py`

## Adventure note
No additional code logic was modified in this pass.
This log was added so future cleanup or refactor work can append entries here instead of relying only on chat history.

## Suggested next adventures
- consolidate duplicate backend entrypoints
- standardize port `9898` references
- add test coverage for bridge / relay startup
- add CI linting for repo layout enforcement
"""

log_path.write_text(content, encoding='utf-8')

# Rezip
if out_zip.exists():
    out_zip.unlink()

with zipfile.ZipFile(out_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for p in root.rglob('*'):
        zf.write(p, arcname=str(p.relative_to(root.parent)))

print(f"Wrote {log_path}")
print(f"Created {out_zip}")
