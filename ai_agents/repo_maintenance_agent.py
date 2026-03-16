#!/usr/bin/env python3
"""
Repository Maintenance Agent

This agent helps maintain the Sovereignty AI Studio repository by:
- Monitoring for misplaced files
- Ensuring proper folder organization
- Cleaning up duplicate files
- Running periodic sanity checks
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Set

# Define the expected directory structure
DIRECTORY_STRUCTURE = {
    'src/crypto': 'C/C++ cryptography files (.hpp, .cpp for Falcon, NTRU, etc.)',
    'src/system-calls': 'System call implementations (.c, .h files)',
    'docs/html': 'HTML documentation and dashboard files',
    'docs/planning': 'Planning and process documentation (.md files)',
    'docs/compliance': 'Compliance and audit documentation',
    'scripts/python': 'Utility Python scripts',
    'scripts/shell': 'Shell scripts for automation',
    'ai_agents': 'AI agent scripts and implementations',
    'archives': 'Archived files (zip, tar.gz, etc.)',
    'backend': 'FastAPI backend services',
    'frontend': 'React frontend application',
    'node-bridge': 'Node.js bridge server',
    'tests': 'Test files',
}

# File type mappings
FILE_TYPE_LOCATIONS = {
    '.hpp': 'src/crypto',
    '.cpp': 'src/crypto',
    '.c': 'src/system-calls',
    '.h': 'src/system-calls',
    '.html': 'docs/html',
    '.zip': 'archives',
    '.tar.gz': 'archives',
}

# Files that should remain in root
ROOT_ALLOWLIST = {
    'package.json',
    'package-lock.json',
    'docker-compose.yml',
    'Dockerfile',
    'Makefile',
    'README.md',
    'LICENSE',
    'LICENSE.MD',
    'SECURITY.md',
    'PORT_ALLOCATION.md',
    '.gitignore',
    '.flake8',
    'pytest.ini',
    'requirements.txt',
    'start-all.sh',
    'START_SERVER.sh',
    'bridge.py',
    'unified_server.js',
    'server_9898.js',
    'server_9898.py',
    'security_backend.py',
    'security_layer.js',
    'node-bridge.mjs',
    'weather_dashboard.py',
}


class RepoMaintenanceAgent:
    """Agent that maintains repository organization and cleanliness."""

    def __init__(self, repo_root: str = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.issues: List[Dict] = []

    def scan_repository(self) -> Dict[str, List[str]]:
        """Scan the repository for organizational issues."""
        print("🔍 Scanning repository structure...")

        misplaced_files = []
        duplicate_files = []
        empty_files = []

        # Check root directory for misplaced files
        for item in self.repo_root.iterdir():
            if item.is_file() and item.name not in ROOT_ALLOWLIST:
                if not item.name.startswith('.'):
                    misplaced_files.append(str(item.name))

            # Check for empty files
            if item.is_file() and item.stat().st_size == 0:
                empty_files.append(str(item.name))

        # Check for duplicate patterns
        seen_names = set()
        for item in self.repo_root.rglob('*'):
            if item.is_file():
                # Check for " 2" or similar duplicate suffixes
                if ' 2.' in item.name or ' 3.' in item.name:
                    duplicate_files.append(str(item.relative_to(self.repo_root)))

        return {
            'misplaced': misplaced_files,
            'duplicates': duplicate_files,
            'empty': empty_files,
        }

    def report_status(self) -> str:
        """Generate a status report of the repository."""
        results = self.scan_repository()

        report = ["=" * 70]
        report.append("📋 REPOSITORY MAINTENANCE REPORT")
        report.append("=" * 70)
        report.append("")

        # Directory structure
        report.append("📁 Expected Directory Structure:")
        for directory, description in DIRECTORY_STRUCTURE.items():
            exists = (self.repo_root / directory).exists()
            status = "✅" if exists else "❌"
            report.append(f"  {status} {directory}: {description}")
        report.append("")

        # Misplaced files
        if results['misplaced']:
            report.append(f"⚠️  Misplaced Files in Root ({len(results['misplaced'])}):")
            for file in results['misplaced'][:10]:  # Show first 10
                report.append(f"  - {file}")
            if len(results['misplaced']) > 10:
                report.append(f"  ... and {len(results['misplaced']) - 10} more")
        else:
            report.append("✅ No misplaced files in root directory")
        report.append("")

        # Duplicate files
        if results['duplicates']:
            report.append(f"⚠️  Potential Duplicate Files ({len(results['duplicates'])}):")
            for file in results['duplicates'][:10]:
                report.append(f"  - {file}")
            if len(results['duplicates']) > 10:
                report.append(f"  ... and {len(results['duplicates']) - 10} more")
        else:
            report.append("✅ No obvious duplicate files found")
        report.append("")

        # Empty files
        if results['empty']:
            report.append(f"⚠️  Empty Files ({len(results['empty'])}):")
            for file in results['empty'][:10]:
                report.append(f"  - {file}")
        else:
            report.append("✅ No empty files found")
        report.append("")

        report.append("=" * 70)

        return "\n".join(report)

    def suggest_fixes(self) -> List[str]:
        """Suggest fixes for identified issues."""
        results = self.scan_repository()
        suggestions = []

        if results['misplaced']:
            suggestions.append("📌 Move misplaced files to appropriate directories:")
            for file in results['misplaced']:
                ext = Path(file).suffix
                if ext in FILE_TYPE_LOCATIONS:
                    suggestions.append(f"  mv {file} {FILE_TYPE_LOCATIONS[ext]}/")

        if results['duplicates']:
            suggestions.append("\n📌 Review and remove duplicate files:")
            for file in results['duplicates']:
                suggestions.append(f"  # Review: {file}")

        if results['empty']:
            suggestions.append("\n📌 Consider removing empty files:")
            for file in results['empty']:
                suggestions.append(f"  rm {file}")

        return suggestions


def main():
    """Main entry point for the maintenance agent."""
    agent = RepoMaintenanceAgent()

    # Print status report
    print(agent.report_status())

    # Print suggestions
    print("\n💡 SUGGESTED ACTIONS:")
    print("=" * 70)
    suggestions = agent.suggest_fixes()
    if suggestions:
        for suggestion in suggestions:
            print(suggestion)
    else:
        print("✅ Repository is well organized! No actions needed.")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    sys.exit(main())
