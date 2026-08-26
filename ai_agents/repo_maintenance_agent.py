#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

REQUIRED_DIRECTORIES = {
    "src/crypto",
    "src/system-calls",
    "docs/html",
    "docs/planning",
    "docs/compliance",
    "scripts/python",
    "scripts/shell",
    "ai_agents",
    "archives",
    "backend",
    "ios",
    "tests",
}

# Forbidden means NEVER create, preserve, or silently ignore.
FORBIDDEN_PATHS = {"frontend"}

FORBIDDEN_DEPENDENCIES = {
    "react",
    "react-dom",
    "react-router",
    "react-router-dom",
    "next",
    "@vitejs/plugin-react",
    "@vitejs/plugin-react-swc",
    "firebase",
    "@firebase",
    "firebase-admin",
    "gemini",
    "@google/generative-ai",
    "google-generativeai",
    "llama",
}

FORBIDDEN_NETWORK_PATTERNS = (
    re.compile(r"(?:https?|wss?)://[^\"'\s]*(?:googleapis\.com|google\.com|googleusercontent\.com|gstatic\.com)", re.I),
    re.compile(r"(?:https?|wss?)://[^\"'\s]*(?:firebaseio\.com|firebaseapp\.com)", re.I),
    re.compile(r"(?:https?|wss?)://[^\"'\s]*(?:facebook\.com|fb\.com|fbcdn\.net|meta\.com)", re.I),
)

INSECURE_TRANSPORT_PATTERNS = (
    re.compile(r"\bhttps?://", re.I),
    re.compile(r"\bws://", re.I),
)

ROOT_ALLOWLIST = {
    ".env.example", ".flake8", ".gitignore", "Dockerfile", "LICENSE", "LICENSE.MD",
    "Makefile", "PORT_ALLOCATION.md", "README.md", "SECURITY.md", "START_SERVER.sh",
    "docker-compose.yml", "package-lock.json", "package.json", "pytest.ini",
    "requirements.txt",
}

SAFE_ROOT_MOVES = {
    "Authorized_Only.html": "docs/html/Authorized_Only.html",
    "SGHv119.html": "docs/html/SGHv119.html",
    "Enterprise_Audio_Platform.swift": "docs/planning/Enterprise_Audio_Platform.md",
    "WebSocket.swift": "docs/planning/WebSocket_Bridge_Notes.md",
    "Nodejs25changeLog_Node.js": "docs/planning/Nodejs25changeLog_Node.md",
    "Uvicorn.run": "scripts/python/uvicorn_9898.py",
    "Sanatizer.js": "scripts/javascript/sanitizer.js",
    "sg_change_log.py": "scripts/python/sg_change_log.py",
}

REPO_SENTINELS = ("README.md", "backend", ".git")


class ActionState(str, Enum):
    DISCOVERED = "DISCOVERED"
    AUTHORIZING = "AUTHORIZING"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    TRIAGE = "TRIAGE"
    AWAITING_OWNER = "AWAITING_OWNER"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Authorization:
    authorized: bool
    actor: str
    capability: str
    reason: str


@dataclass
class ActionEvent:
    action_id: str
    operation: str
    path: str
    state: ActionState
    reason: str
    owner_decision_required: bool = False


@dataclass
class ScanResults:
    misplaced: List[str] = field(default_factory=list)
    duplicates: List[str] = field(default_factory=list)
    empty: List[str] = field(default_factory=list)
    missing_directories: List[str] = field(default_factory=list)
    forbidden_paths: List[str] = field(default_factory=list)
    forbidden_dependencies: List[str] = field(default_factory=list)
    forbidden_network_targets: List[str] = field(default_factory=list)
    insecure_transports: List[str] = field(default_factory=list)


class MaintenanceAuthorizationError(RuntimeError):
    pass


class UnsafeRepositoryError(RuntimeError):
    pass


class RepoMaintenanceAgent:
    def __init__(self, repo_root: Optional[str] = None, authorization: Optional[Authorization] = None):
        start = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
        self.repo_root = self._resolve_repo_root(start)
        self.authorization = authorization

    def _resolve_repo_root(self, start: Path) -> Path:
        for candidate in (start, *start.parents):
            if all((candidate / sentinel).exists() for sentinel in REPO_SENTINELS):
                return candidate
        return start

    def _validate_repo_root(self) -> None:
        if not self.repo_root.exists() or not self.repo_root.is_dir():
            raise UnsafeRepositoryError(f"Invalid repository root: {self.repo_root}")
        if self.repo_root == Path("/"):
            raise UnsafeRepositoryError("Refusing to operate on filesystem root")
        if not (self.repo_root / ".git").exists():
            raise UnsafeRepositoryError(f"Not a Git repository: {self.repo_root}")

    def _require_authorization(self, capability: str) -> None:
        auth = self.authorization
        if auth is None or not auth.authorized:
            raise MaintenanceAuthorizationError("Mutation denied: explicit owner authorization is required")
        if auth.capability != capability:
            raise MaintenanceAuthorizationError(
                f"Mutation denied: capability {capability!r} was not authorized"
            )
        if not auth.actor.strip() or not auth.reason.strip():
            raise MaintenanceAuthorizationError("Mutation denied: actor and reason are required")

    def emit(self, event: ActionEvent) -> None:
        print(json.dumps({
            "type": "maintenance_event",
            "action_id": event.action_id,
            "operation": event.operation,
            "path": event.path,
            "state": event.state.value,
            "reason": event.reason,
            "owner_decision_required": event.owner_decision_required,
        }, sort_keys=True), flush=True)

    def scan_forbidden_paths(self) -> List[str]:
        return sorted(
            rel for rel in FORBIDDEN_PATHS
            if (self.repo_root / rel).exists()
        )

    def scan_forbidden_dependencies(self) -> List[str]:
        findings: List[str] = []
        forbidden = {d.lower() for d in FORBIDDEN_DEPENDENCIES}
        for package_json in self.repo_root.rglob("package.json"):
            if any(part in {".git", "node_modules"} for part in package_json.parts):
                continue
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                findings.append(f"unreadable:{package_json.relative_to(self.repo_root)}")
                continue
            for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                deps = data.get(section, {})
                if not isinstance(deps, dict):
                    continue
                for dependency in deps:
                    if dependency.lower() in forbidden:
                        findings.append(
                            f"{package_json.relative_to(self.repo_root)}:{section}:{dependency}"
                        )
        return sorted(set(findings))

    def scan_forbidden_network_targets(self) -> List[str]:
        return self._scan_patterns(FORBIDDEN_NETWORK_PATTERNS)

    def scan_insecure_transports(self) -> List[str]:
        return self._scan_patterns(INSECURE_TRANSPORT_PATTERNS)

    def _scan_patterns(self, patterns: tuple[re.Pattern[str], ...]) -> List[str]:
        findings: List[str] = []
        extensions = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".toml", ".sh", ".bash", ".zsh", ".env", ".conf"}
        ignored = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        for path in self.repo_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            if any(part in ignored for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(pattern.search(text) for pattern in patterns):
                findings.append(str(path.relative_to(self.repo_root)))
        return sorted(set(findings))

    def scan_repository(self) -> ScanResults:
        self._validate_repo_root()
        results = ScanResults()
        results.missing_directories = sorted(
            directory for directory in REQUIRED_DIRECTORIES
            if not (self.repo_root / directory).exists()
        )
        results.forbidden_paths = self.scan_forbidden_paths()
        results.forbidden_dependencies = self.scan_forbidden_dependencies()
        results.forbidden_network_targets = self.scan_forbidden_network_targets()
        results.insecure_transports = self.scan_insecure_transports()

        for item in sorted(self.repo_root.iterdir()):
            if item.is_file():
                if item.name not in ROOT_ALLOWLIST and not item.name.startswith("."):
                    results.misplaced.append(item.name)
                if item.stat().st_size == 0:
                    results.empty.append(item.name)

        for item in self.repo_root.rglob("*"):
            if item.is_file() and (" 2." in item.name or " 3." in item.name or item.name.endswith(" copy")):
                results.duplicates.append(str(item.relative_to(self.repo_root)))

        results.duplicates.sort()
        results.empty.sort()
        results.misplaced.sort()
        return results

    def apply_safe_fixes(self, dry_run: bool = True) -> List[str]:
        self._validate_repo_root()
        actions: List[str] = []

        # Forbidden paths are remediation targets, never required structure.
        for rel_path in self.scan_forbidden_paths():
            actions.append(f"remove forbidden path {rel_path}")
            if not dry_run:
                self._require_authorization("repo.remove_forbidden_path")
                self.emit(ActionEvent(rel_path, "remove", rel_path, ActionState.RUNNING, "forbidden path remediation"))
                shutil.rmtree(self.repo_root / rel_path)
                self.emit(ActionEvent(rel_path, "remove", rel_path, ActionState.COMPLETED, "verified removal"))

        # React dependency cleanup is explicit and cannot create a frontend.
        if self.scan_forbidden_dependencies():
            actions.append("remove forbidden package dependencies")
            if not dry_run:
                self._require_authorization("repo.remove_forbidden_dependencies")
                for package_json in self.repo_root.rglob("package.json"):
                    if any(part in {".git", "node_modules"} for part in package_json.parts):
                        continue
                    try:
                        data = json.loads(package_json.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    changed = False
                    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                        deps = data.get(section, {})
                        if not isinstance(deps, dict):
                            continue
                        for dependency in list(deps):
                            if dependency.lower() in {d.lower() for d in FORBIDDEN_DEPENDENCIES}:
                                del deps[dependency]
                                changed = True
                    if changed:
                        package_json.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        # Safe moves remain bounded and authorized.
        for src_name, rel_dest in SAFE_ROOT_MOVES.items():
            src = self.repo_root / src_name
            dest = self.repo_root / rel_dest
            if not src.exists():
                continue
            actions.append(f"move {src_name} -> {rel_dest}")
            if not dry_run:
                self._require_authorization("repo.move_artifact")
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))

        # Only required directories are created. Forbidden directories are never recreated.
        for directory in sorted(REQUIRED_DIRECTORIES):
            path = self.repo_root / directory
            if not path.exists():
                actions.append(f"create {directory}")
                if not dry_run:
                    self._require_authorization("repo.create_directory")
                    path.mkdir(parents=True, exist_ok=True)

        return actions

    def suggest_fixes(self, results: Optional[ScanResults] = None) -> List[str]:
        results = results or self.scan_repository()
        suggestions: List[str] = []
        if results.forbidden_paths:
            suggestions.append("TRIAGE: forbidden paths require owner-approved removal")
            suggestions.extend(f"  repair candidate: remove {path}" for path in results.forbidden_paths)
        if results.forbidden_dependencies:
            suggestions.append("TRIAGE: forbidden dependencies require owner-approved removal")
            suggestions.extend(f"  repair candidate: {item}" for item in results.forbidden_dependencies)
        if results.forbidden_network_targets:
            suggestions.append("BLOCK: unauthorized network destinations detected")
            suggestions.extend(f"  blocked source: {item}" for item in results.forbidden_network_targets)
        if results.insecure_transports:
            suggestions.append("BLOCK: insecure transport reference detected; production transport must be HTTPS/WSS")
            suggestions.extend(f"  insecure source: {item}" for item in results.insecure_transports)
        if results.misplaced:
            suggestions.append("Review misplaced root files:")
            suggestions.extend(f"  # review placement: {file}" for file in results.misplaced)
        if results.duplicates:
            suggestions.append("Review likely duplicate files:")
            suggestions.extend(f"  # review duplicate: {file}" for file in results.duplicates)
        if results.empty:
            suggestions.append("Review empty files:")
            suggestions.extend(f"  # review empty file: {file}" for file in results.empty)
        return suggestions

    def report_status(self, as_json: bool = False) -> str:
        results = self.scan_repository()
        payload = {
            "repo_root": str(self.repo_root),
            "required_directories": sorted(REQUIRED_DIRECTORIES),
            "forbidden_paths": results.forbidden_paths,
            "forbidden_dependencies": results.forbidden_dependencies,
            "forbidden_network_targets": results.forbidden_network_targets,
            "insecure_transports": results.insecure_transports,
            "missing_directories": results.missing_directories,
            "misplaced": results.misplaced,
            "duplicates": results.duplicates,
            "empty": results.empty,
            "suggestions": self.suggest_fixes(results),
        }
        if as_json:
            return json.dumps(payload, indent=2, sort_keys=True)
        lines = ["=" * 70, "REPOSITORY MAINTENANCE REPORT", "=" * 70, f"Repo root: {self.repo_root}", ""]
        lines.append("Required directories:")
        for directory in sorted(REQUIRED_DIRECTORIES):
            status = "OK" if (self.repo_root / directory).exists() else "MISSING"
            lines.append(f"  [{status}] {directory}")
        lines.extend([
            "",
            f"Forbidden paths: {len(results.forbidden_paths)}",
            f"Forbidden dependencies: {len(results.forbidden_dependencies)}",
            f"Forbidden network targets: {len(results.forbidden_network_targets)}",
            f"Insecure transports: {len(results.insecure_transports)}",
            f"Misplaced root files: {len(results.misplaced)}",
            f"Potential duplicates: {len(results.duplicates)}",
            f"Empty files: {len(results.empty)}",
            "",
            "Suggested actions:",
        ])
        lines.extend(f"  {item}" for item in self.suggest_fixes(results))
        lines.append("=" * 70)
        return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain Sovereignty AI Studio repository structure and transport policy.")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--actor", default="")
    parser.add_argument("--reason", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.fix and args.dry_run:
        print("ERROR: --fix and --dry-run are mutually exclusive", file=sys.stderr)
        return 2

    authorization = Authorization(
        authorized=args.fix,
        actor=args.actor,
        capability="repo.create_directory" if args.fix else "",
        reason=args.reason,
    ) if args.fix else None

    agent = RepoMaintenanceAgent(repo_root=args.repo_root, authorization=authorization)
    if args.fix:
        # A fix is never a dry run. Individual operations require their own capability;
        # callers using this CLI should supply a capability-aware integration for mutations.
        try:
            actions = agent.apply_safe_fixes(dry_run=False)
        except MaintenanceAuthorizationError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 3
        if actions:
            print("Applied actions:")
            for action in actions:
                print(f"  - {action}")
    elif args.dry_run:
        actions = agent.apply_safe_fixes(dry_run=True)
        if actions:
            print("Planned actions:")
            for action in actions:
                print(f"  - {action}")

    print(agent.report_status(as_json=args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
