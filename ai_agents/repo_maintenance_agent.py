#!/usr/bin/env python3
"""Repository maintenance agent — scan and report only by default.

Owner (Appel420) must explicitly approve any apply (--fix).
No React / Meta / Vercel assumptions. Sovereign structure only.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Expected layout (no React, no forbidden providers)
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
    'backend': 'FastAPI / local backend services',
    'frontend': 'Sovereign UI (static HTML/JS or approved local stack — not React/Meta)',
    'node-bridge': 'Node.js bridge server',
    'ios': 'iOS and Swift sources',
    'tests': 'Test files',
    '.github/workflows': 'GitHub Actions workflows',
    'config': 'Owner and runtime policy JSON',
}

ROOT_ALLOWLIST = {
    '.env.example', '.flake8', '.gitignore', 'Dockerfile', 'LICENSE', 'LICENSE.MD',
    'Makefile', 'PORT_ALLOCATION.md', 'README.md', 'SECURITY.md', 'START_SERVER.sh',
    'bridge.py', 'docker-compose.yml', 'ecosystem.config.cjs', 'node-bridge.mjs',
    'package-lock.json', 'package.json', 'pytest.ini', 'requirements.txt',
    'security_backend.py', 'security_layer.js', 'server_9898.js', 'server_9898.py',
    'start-all.sh', 'unified_server.js', 'weather_dashboard.py', 'pyproject.toml',
    'AGENTS.md',
}

# Only applied when owner passes --fix AND --i-approve-moves
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

# Do not require frontend (may be static-only); require core sentinels only
REPO_SENTINELS = ('package.json', 'README.md', 'backend', 'node-bridge')

FORBIDDEN_MARKERS = ('react', 'meta', 'vercel', 'next.js', 'create-react-app')


@dataclass
class ScanResults:
    misplaced: List[str]
    duplicates: List[str]
    empty: List[str]
    missing_directories: List[str]
    forbidden_hits: List[str]


class RepoMaintenanceAgent:
    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = self._resolve_repo_root(
            Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
        )

    def _resolve_repo_root(self, start: Path) -> Path:
        for candidate in [start, *start.parents]:
            if all((candidate / s).exists() for s in REPO_SENTINELS):
                return candidate
        return start

    def scan_repository(self) -> ScanResults:
        misplaced: List[str] = []
        duplicates: List[str] = []
        empty: List[str] = []
        missing: List[str] = []
        forbidden: List[str] = []

        for directory in DIRECTORY_STRUCTURE:
            if not (self.repo_root / directory).exists():
                missing.append(directory)

        for item in sorted(self.repo_root.iterdir()):
            if item.is_file():
                if item.name not in ROOT_ALLOWLIST and not item.name.startswith('.'):
                    misplaced.append(item.name)
                if item.stat().st_size == 0:
                    empty.append(item.name)

        for item in self.repo_root.rglob('*'):
            if not item.is_file():
                continue
            rel = str(item.relative_to(self.repo_root))
            name = item.name
            if ' 2.' in name or ' 3.' in name or name.endswith(' copy'):
                duplicates.append(rel)
            lower = rel.lower()
            for marker in FORBIDDEN_MARKERS:
                if marker in lower and 'node_modules' not in lower:
                    forbidden.append(rel)
                    break

        return ScanResults(
            misplaced=misplaced,
            duplicates=sorted(duplicates),
            empty=sorted(empty),
            missing_directories=missing,
            forbidden_hits=sorted(set(forbidden)),
        )

    def apply_safe_fixes(self, dry_run: bool = True, owner_approved: bool = False) -> List[str]:
        """Moves only when owner_approved=True. Default is dry-run / no-op."""
        if not owner_approved and not dry_run:
            return ['BLOCKED: --fix requires --i-approve-moves (owner decision)']

        actions: List[str] = []
        for src_name, rel_dest in SAFE_ROOT_MOVES.items():
            src = self.repo_root / src_name
            dest = self.repo_root / rel_dest
            if not src.exists():
                continue
            actions.append(f'move {src_name} -> {rel_dest}')
            if not dry_run and owner_approved:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))

        for directory in DIRECTORY_STRUCTURE:
            path = self.repo_root / directory
            if not path.exists():
                actions.append(f'create {directory} (report only unless owner approved)')
                if not dry_run and owner_approved:
                    path.mkdir(parents=True, exist_ok=True)
        return actions

    def suggest_fixes(self, results: Optional[ScanResults] = None) -> List[str]:
        results = results or self.scan_repository()
        suggestions: List[str] = []
        if results.forbidden_hits:
            suggestions.append('FORBIDDEN markers (React/Meta/Vercel etc.) — review:')
            suggestions.extend(f'  # forbidden: {f}' for f in results.forbidden_hits[:30])
        if results.misplaced:
            suggestions.append('Misplaced root files (owner must approve any move):')
            for file in results.misplaced:
                if file in SAFE_ROOT_MOVES:
                    suggestions.append(f'  # suggested: mv {file} {SAFE_ROOT_MOVES[file]}')
                else:
                    suggestions.append(f'  # review placement: {file}')
        if results.duplicates:
            suggestions.append('Likely duplicate files:')
            suggestions.extend(f'  # review duplicate: {f}' for f in results.duplicates)
        if results.empty:
            suggestions.append('Empty files:')
            suggestions.extend(f'  # review empty: {f}' for f in results.empty)
        return suggestions

    def report_status(self, as_json: bool = False) -> str:
        results = self.scan_repository()
        payload = {
            'repo_root': str(self.repo_root),
            'missing_directories': results.missing_directories,
            'misplaced': results.misplaced,
            'duplicates': results.duplicates,
            'empty': results.empty,
            'forbidden_hits': results.forbidden_hits,
            'suggestions': self.suggest_fixes(results),
            'policy': 'report-only by default; --fix requires --i-approve-moves',
        }
        if as_json:
            return json.dumps(payload, indent=2)

        lines = [
            '=' * 70,
            'REPOSITORY MAINTENANCE REPORT',
            '=' * 70,
            f'Repo root: {self.repo_root}',
            'Mode: scan/report (no silent moves)',
            '',
            'Expected directory structure:',
        ]
        for directory, description in DIRECTORY_STRUCTURE.items():
            status = 'OK' if (self.repo_root / directory).exists() else 'MISSING'
            lines.append(f'  [{status}] {directory}: {description}')
        lines.append('')
        if results.forbidden_hits:
            lines.append(f'FORBIDDEN markers ({len(results.forbidden_hits)}):')
            lines.extend(f'  - {f}' for f in results.forbidden_hits[:20])
        else:
            lines.append('No forbidden React/Meta/Vercel path markers found')
        lines.append('')
        if results.misplaced:
            lines.append(f'Misplaced files in root ({len(results.misplaced)}):')
            lines.extend(f'  - {f}' for f in results.misplaced)
        else:
            lines.append('No misplaced files in root directory')
        lines.append('')
        if results.duplicates:
            lines.append(f'Potential duplicates ({len(results.duplicates)}):')
            lines.extend(f'  - {f}' for f in results.duplicates[:20])
        else:
            lines.append('No obvious duplicate files found')
        lines.append('')
        if results.empty:
            lines.append(f'Empty files ({len(results.empty)}):')
            lines.extend(f'  - {f}' for f in results.empty[:20])
        else:
            lines.append('No empty files found')
        lines.append('')
        suggestions = payload['suggestions']
        if suggestions:
            lines.append('Suggested actions (owner must approve applies):')
            lines.extend(suggestions)
        else:
            lines.append('No suggested actions')
        lines.append('=' * 70)
        return '\n'.join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description='Maintain Sovereignty AI Studio structure. Report-only by default.'
    )
    p.add_argument('--repo-root', default=None)
    p.add_argument('--json', action='store_true')
    p.add_argument('--fix', action='store_true', help='Apply moves (requires --i-approve-moves)')
    p.add_argument(
        '--i-approve-moves',
        action='store_true',
        help='Owner acknowledgment required with --fix',
    )
    p.add_argument('--dry-run', action='store_true', help='Show planned moves only')
    return p


def main() -> int:
    args = build_parser().parse_args()
    agent = RepoMaintenanceAgent(repo_root=args.repo_root)

    if args.fix or args.dry_run:
        actions = agent.apply_safe_fixes(
            dry_run=not args.fix,
            owner_approved=bool(args.i_approve_moves),
        )
        if actions:
            label = 'Applied actions:' if (args.fix and args.i_approve_moves) else 'Planned / blocked actions:'
            print(label)
            for action in actions:
                print(f'  - {action}')
            print('')

    print(agent.report_status(as_json=args.json))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
