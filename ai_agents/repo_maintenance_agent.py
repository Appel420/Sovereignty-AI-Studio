#!/usr/bin/env python3
"""Repository maintenance agent — scan/report by default; apply only with owner approval.

- Detects React/Meta/Vercel markers
- On --fix --i-approve-moves: removes React source tree, keeps static HTML
- Never deletes node-bridge (sovereign entrypoint)
- No silent dry-run when --fix is set without approval (hard block)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

DIRECTORY_STRUCTURE = {
    'src/crypto': 'C/C++ cryptography files',
    'src/system-calls': 'System call implementations',
    'docs/html': 'HTML documentation and dashboard files',
    'docs/planning': 'Planning and process documentation',
    'docs/compliance': 'Compliance and audit documentation',
    'scripts/python': 'Utility Python scripts',
    'scripts/shell': 'Shell scripts for automation',
    'scripts/javascript': 'Utility Node.js scripts',
    'ai_agents': 'AI agent scripts',
    'archives': 'Archived files',
    'backend': 'Local backend services',
    'frontend': 'Sovereign static UI only (no React/Meta)',
    'node-bridge': 'Node.js bridge server (required — do not delete)',
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

REPO_SENTINELS = ('package.json', 'README.md', 'backend', 'node-bridge')

FORBIDDEN_PATH_MARKERS = (
    'react', 'react-dom', 'react-router', 'next.js', 'create-react-app',
    'vercel', '@meta', 'facebook',
)

REACT_CONTENT_PATTERNS = (
    re.compile(r"from ['\"]react['\"]"),
    re.compile(r"from ['\"]react-dom"),
    re.compile(r"from ['\"]react-router"),
    re.compile(r"require\(['\"]react['\"]\)"),
    re.compile(r"@heroicons/react"),
)

# Paths under frontend that are React application code (purge targets)
REACT_PURGE_PATHS = (
    'frontend/src',
    'frontend/tsconfig.json',
    'frontend/postcss.config.js',
)

# Never delete these even if under frontend
PRESERVE_UNDER_FRONTEND = (
    'frontend/index.html',
    'frontend/public',
    'frontend/dashboard',
    'frontend/views',
    'frontend/q-resist-dashboard.html',
    'frontend/xai-grok-terminal.html',
    'frontend/runtime',
    'frontend/scripts',
)


@dataclass
class ScanResults:
    misplaced: List[str] = field(default_factory=list)
    duplicates: List[str] = field(default_factory=list)
    empty: List[str] = field(default_factory=list)
    missing_directories: List[str] = field(default_factory=list)
    forbidden_hits: List[str] = field(default_factory=list)
    react_detected: bool = False
    react_paths: List[str] = field(default_factory=list)


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

    def _file_has_react_content(self, path: Path) -> bool:
        try:
            text = path.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            return False
        return any(p.search(text) for p in REACT_CONTENT_PATTERNS)

    def scan_repository(self) -> ScanResults:
        results = ScanResults()

        for directory in DIRECTORY_STRUCTURE:
            if not (self.repo_root / directory).exists():
                results.missing_directories.append(directory)

        for item in sorted(self.repo_root.iterdir()):
            if item.is_file():
                if item.name not in ROOT_ALLOWLIST and not item.name.startswith('.'):
                    results.misplaced.append(item.name)
                if item.stat().st_size == 0:
                    results.empty.append(item.name)

        for item in self.repo_root.rglob('*'):
            if not item.is_file():
                continue
            rel = str(item.relative_to(self.repo_root))
            lower = rel.lower()
            if 'node_modules' in lower or '/.git/' in lower:
                continue
            if ' 2.' in item.name or ' 3.' in item.name or item.name.endswith(' copy'):
                results.duplicates.append(rel)
            for marker in FORBIDDEN_PATH_MARKERS:
                if marker in lower:
                    results.forbidden_hits.append(rel)
                    break
            if rel.startswith('frontend/') and item.suffix in {
                '.tsx', '.jsx', '.ts', '.js', '.css',
            }:
                if self._file_has_react_content(item):
                    results.react_detected = True
                    results.react_paths.append(rel)

        # Path-based React tree detection
        src = self.repo_root / 'frontend' / 'src'
        if src.is_dir():
            for p in src.rglob('*'):
                if p.is_file() and p.suffix in {'.tsx', '.jsx'}:
                    results.react_detected = True
                    rel = str(p.relative_to(self.repo_root))
                    if rel not in results.react_paths:
                        results.react_paths.append(rel)

        results.duplicates = sorted(set(results.duplicates))
        results.empty = sorted(set(results.empty))
        results.forbidden_hits = sorted(set(results.forbidden_hits))
        results.react_paths = sorted(set(results.react_paths))
        return results

    def purge_react(self, dry_run: bool, owner_approved: bool) -> List[str]:
        """Remove React application code; keep static HTML surfaces."""
        actions: List[str] = []
        if not owner_approved:
            return ['BLOCKED: React purge requires --fix --i-approve-moves']

        frontend = self.repo_root / 'frontend'
        if not frontend.exists():
            actions.append('frontend/ absent — nothing to purge')
            return actions

        # Remove known React trees/files
        for rel in REACT_PURGE_PATHS:
            path = self.repo_root / rel
            if path.exists():
                actions.append(f'purge React path: {rel}')
                if not dry_run:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()

        # Remove any remaining .tsx/.jsx under frontend
        if frontend.exists():
            for p in list(frontend.rglob('*')):
                if p.is_file() and p.suffix in {'.tsx', '.jsx'}:
                    rel = str(p.relative_to(self.repo_root))
                    actions.append(f'purge React file: {rel}')
                    if not dry_run:
                        p.unlink()

        # Neutralize React Dockerfile if present
        docker = frontend / 'Dockerfile'
        if docker.exists():
            actions.append('remove frontend/Dockerfile (Node/React app image)')
            if not dry_run:
                docker.unlink()

        # Note: node-bridge is never touched
        actions.append('preserved: node-bridge/ (sovereign entrypoint)')
        actions.append('preserved: static HTML under frontend/ if present')
        return actions

    def apply_safe_fixes(
        self,
        dry_run: bool = True,
        owner_approved: bool = False,
        purge_react: bool = False,
    ) -> List[str]:
        if not dry_run and not owner_approved:
            return [
                'BLOCKED: --fix requires --i-approve-moves (owner decision). '
                'No dry-run substitute. Refusing to apply.'
            ]

        actions: List[str] = []

        if purge_react:
            actions.extend(self.purge_react(dry_run=dry_run, owner_approved=owner_approved))

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
            # Do not auto-create a React frontend — only static placeholder note
            path = self.repo_root / directory
            if not path.exists():
                actions.append(f'missing directory (not auto-created): {directory}')

        return actions

    def suggest_fixes(self, results: Optional[ScanResults] = None) -> List[str]:
        results = results or self.scan_repository()
        suggestions: List[str] = []
        if results.react_detected:
            suggestions.append(
                'REACT DETECTED under frontend/ — run with '
                '--fix --i-approve-moves --purge-react to remove React tree '
                '(static HTML kept; node-bridge never deleted)'
            )
            suggestions.extend(f'  # react: {p}' for p in results.react_paths[:25])
        if results.forbidden_hits:
            suggestions.append('FORBIDDEN path markers:')
            suggestions.extend(f'  # forbidden: {f}' for f in results.forbidden_hits[:20])
        if results.misplaced:
            suggestions.append('Misplaced root files:')
            for file in results.misplaced:
                if file in SAFE_ROOT_MOVES:
                    suggestions.append(f'  # suggested: mv {file} {SAFE_ROOT_MOVES[file]}')
                else:
                    suggestions.append(f'  # review: {file}')
        return suggestions

    def report_status(self, as_json: bool = False) -> str:
        results = self.scan_repository()
        payload = {
            'repo_root': str(self.repo_root),
            'react_detected': results.react_detected,
            'react_paths_sample': results.react_paths[:40],
            'missing_directories': results.missing_directories,
            'misplaced': results.misplaced,
            'duplicates': results.duplicates[:40],
            'empty': results.empty[:40],
            'forbidden_hits': results.forbidden_hits[:40],
            'suggestions': self.suggest_fixes(results),
            'policy': {
                'default': 'report-only',
                'apply': '--fix --i-approve-moves',
                'react_purge': '--fix --i-approve-moves --purge-react',
                'never_delete': ['node-bridge'],
            },
        }
        if as_json:
            return json.dumps(payload, indent=2)

        lines = [
            '=' * 70,
            'REPOSITORY MAINTENANCE REPORT',
            '=' * 70,
            f'Repo root: {self.repo_root}',
            'Default mode: scan/report only',
            '',
        ]
        if results.react_detected:
            lines.append(f'REACT DETECTED ({len(results.react_paths)} files)')
            lines.extend(f'  - {p}' for p in results.react_paths[:15])
            lines.append(
                '  Action: python ai_agents/repo_maintenance_agent.py '
                '--fix --i-approve-moves --purge-react'
            )
        else:
            lines.append('No React application sources detected')
        lines.append('')
        if results.forbidden_hits:
            lines.append(f'Forbidden markers ({len(results.forbidden_hits)}):')
            lines.extend(f'  - {f}' for f in results.forbidden_hits[:15])
        else:
            lines.append('No forbidden path markers')
        lines.append('')
        lines.append(
            f'Misplaced root files: {len(results.misplaced)} | '
            f'Duplicates: {len(results.duplicates)} | Empty: {len(results.empty)}'
        )
        suggestions = payload['suggestions']
        if suggestions:
            lines.append('Suggestions:')
            lines.extend(suggestions[:40])
        lines.append('=' * 70)
        return '\n'.join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description='Sovereignty repo maintenance. Report-only unless owner approves.'
    )
    p.add_argument('--repo-root', default=None)
    p.add_argument('--json', action='store_true')
    p.add_argument(
        '--fix',
        action='store_true',
        help='Apply changes (requires --i-approve-moves; no silent dry-run)',
    )
    p.add_argument(
        '--i-approve-moves',
        action='store_true',
        help='Owner acknowledgment required with --fix',
    )
    p.add_argument(
        '--purge-react',
        action='store_true',
        help='With --fix --i-approve-moves: remove React tree; keep static HTML',
    )
    p.add_argument('--dry-run', action='store_true', help='Plan only (explicit)')
    return p


def main() -> int:
    args = build_parser().parse_args()
    agent = RepoMaintenanceAgent(repo_root=args.repo_root)

    if args.fix or args.dry_run or args.purge_react:
        # --fix without approval is a hard block (not a quiet dry-run)
        dry = (not args.fix) or args.dry_run
        actions = agent.apply_safe_fixes(
            dry_run=dry,
            owner_approved=bool(args.i_approve_moves),
            purge_react=bool(args.purge_react),
        )
        if actions:
            if args.fix and args.i_approve_moves and not args.dry_run:
                label = 'Applied actions:'
            elif args.fix and not args.i_approve_moves:
                label = 'BLOCKED (owner approval missing):'
            else:
                label = 'Planned actions (dry-run):'
            print(label)
            for action in actions:
                print(f'  - {action}')
            print('')

    print(agent.report_status(as_json=args.json))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
