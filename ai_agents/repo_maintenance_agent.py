#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
DIRECTORY_STRUCTURE = {
    'src/crypto': 'C/C++ cryptography files (.hpp, .cpp for Falcon, NTRU, etc.)',
    'src/system-calls': 'System call implementations (.c, .h files)',
    'docs/html': 'HTML documentation and dashboard files',
    'docs/planning': 'Planning, blueprints, and process documentation',
    'docs/compliance': 'Compliance and audit documentation',
    'scripts/python': 'Utility Python scripts',
    'scripts/shell': 'Shell scripts for automation',
    'scripts/javascript': 'Utility Node.js and browser-side scripts',
    'ai_agents': 'AI agent scripts and implementations',
    'archives': 'Archived files (zip, tar.gz, etc.)',
    'backend': 'FastAPI backend services',
    'frontend': 'React frontend application',
    'node-bridge': 'Node.js bridge server',
    'ios': 'iOS and Swift sources',
    'tests': 'Test files',
}
ROOT_ALLOWLIST = {
    '.env.example','.flake8','.gitignore','Dockerfile','LICENSE','LICENSE.MD','Makefile',
    'PORT_ALLOCATION.md','README.md','SECURITY.md','START_SERVER.sh','bridge.py',
    'docker-compose.yml','ecosystem.config.cjs','node-bridge.mjs','package-lock.json',
    'package.json','pytest.ini','requirements.txt','security_backend.py','security_layer.js',
    'server_9898.js','server_9898.py','start-all.sh','unified_server.js','weather_dashboard.py',
}
SAFE_ROOT_MOVES = {
    'Authorized_Only.html': 'docs/html/Authorized_Only.html',
    'SGHv119.html': 'docs/html/SGHv119.html',
    'Enterprise_Audio_Platform.swift': 'docs/planning/Enterprise_Audio_Platform.md',
    'WebSocket.swift': 'docs/planning/WebSocket_Bridge_Notes.md',
    'Nodejs25changeLog_Node.js': 'docs/planning/Nodejs25changeLog_Node.md',
    'Uvicorn.run': 'scripts/python/uvicorn_9898.py',
    'Sanatizer.js': 'scripts/javascript/sanitizer.js',
    'sg_change_log.py': 'scripts/python/sg_change_log.py',
}
REPO_SENTINELS = ('package.json', 'README.md', 'backend', 'frontend', 'node-bridge')
@dataclass
class ScanResults:
    misplaced: List[str]
    duplicates: List[str]
    empty: List[str]
    missing_directories: List[str]
class RepoMaintenanceAgent:
    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = self._resolve_repo_root(Path(repo_root).resolve() if repo_root else Path.cwd().resolve())
    def _resolve_repo_root(self, start: Path) -> Path:
        for candidate in [start, *start.parents]:
            if all((candidate / s).exists() for s in REPO_SENTINELS):
                return candidate
        return start
    def scan_repository(self) -> ScanResults:
        misplaced=[]; duplicates=[]; empty=[]; missing=[]
        for directory in DIRECTORY_STRUCTURE:
            if not (self.repo_root / directory).exists(): missing.append(directory)
        for item in sorted(self.repo_root.iterdir()):
            if item.is_file():
                if item.name not in ROOT_ALLOWLIST and not item.name.startswith('.'): misplaced.append(item.name)
                if item.stat().st_size == 0: empty.append(item.name)
        for item in self.repo_root.rglob('*'):
            if item.is_file() and (' 2.' in item.name or ' 3.' in item.name or item.name.endswith(' copy')):
                duplicates.append(str(item.relative_to(self.repo_root)))
        return ScanResults(misplaced, sorted(duplicates), sorted(empty), missing)
    def apply_safe_fixes(self, dry_run: bool = True) -> List[str]:
        actions=[]
        for src_name, rel_dest in SAFE_ROOT_MOVES.items():
            src=self.repo_root / src_name; dest=self.repo_root / rel_dest
            if not src.exists(): continue
            actions.append(f'move {src_name} -> {rel_dest}')
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(src), str(dest))
        for directory in DIRECTORY_STRUCTURE:
            path=self.repo_root / directory
            if not path.exists():
                actions.append(f'create {directory}')
                if not dry_run: path.mkdir(parents=True, exist_ok=True)
        return actions
    def suggest_fixes(self, results: Optional[ScanResults] = None) -> List[str]:
        results = results or self.scan_repository(); suggestions=[]
        if results.misplaced:
            suggestions.append('Move misplaced files to appropriate directories:')
            for file in results.misplaced:
                suggestions.append(f"  mv {file} {SAFE_ROOT_MOVES[file]}" if file in SAFE_ROOT_MOVES else f'  # review placement: {file}')
        if results.duplicates:
            suggestions.append('Review likely duplicate files:')
            suggestions.extend(f'  # review duplicate: {f}' for f in results.duplicates)
        if results.empty:
            suggestions.append('Review empty files:')
            suggestions.extend(f'  # review empty file: {f}' for f in results.empty)
        return suggestions
    def report_status(self, as_json: bool = False) -> str:
        results = self.scan_repository()
        payload = {
            'repo_root': str(self.repo_root),
            'missing_directories': results.missing_directories,
            'misplaced': results.misplaced,
            'duplicates': results.duplicates,
            'empty': results.empty,
            'suggestions': self.suggest_fixes(results),
        }
        if as_json: return json.dumps(payload, indent=2)
        lines=['='*70,'REPOSITORY MAINTENANCE REPORT','='*70,f'Repo root: {self.repo_root}','','Expected Directory Structure:']
        for directory, description in DIRECTORY_STRUCTURE.items():
            status='OK' if (self.repo_root / directory).exists() else 'MISSING'
            lines.append(f'  [{status}] {directory}: {description}')
        lines.append('')
        lines.append('No misplaced files in root directory' if not results.misplaced else f'Misplaced files in root ({len(results.misplaced)}):')
        if results.misplaced: lines.extend(f'  - {f}' for f in results.misplaced)
        lines.append('')
        lines.append('No obvious duplicate files found' if not results.duplicates else f'Potential duplicate files ({len(results.duplicates)}):')
        if results.duplicates: lines.extend(f'  - {f}' for f in results.duplicates[:20])
        lines.append('')
        lines.append('No empty files found' if not results.empty else f'Empty files ({len(results.empty)}):')
        if results.empty: lines.extend(f'  - {f}' for f in results.empty[:20])
        lines.append('')
        lines.append('No suggested actions' if not payload['suggestions'] else 'Suggested actions:')
        if payload['suggestions']: lines.extend(payload['suggestions'])
        lines.append('='*70)
        return '\n'.join(lines)

def build_parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description='Maintain Sovereignty AI Studio repository structure.')
    p.add_argument('--repo-root', default=None)
    p.add_argument('--json', action='store_true')
    p.add_argument('--fix', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    return p

def main() -> int:
    args=build_parser().parse_args(); agent=RepoMaintenanceAgent(repo_root=args.repo_root)
    if args.fix or args.dry_run:
        actions=agent.apply_safe_fixes(dry_run=not args.fix)
        if actions:
            print('Applied actions:' if args.fix else 'Planned actions:')
            for action in actions: print(f'  - {action}')
            print('')
    print(agent.report_status(as_json=args.json)); return 0
if __name__ == '__main__': raise SystemExit(main())
