#!/usr/bin/env python3
"""Determine the minimal deterministic CI scope for a set of changed paths.

This module is deliberately read-only: it only classifies paths supplied by the
caller.  It does not invoke Git, modify the repository, install dependencies,
or access the network.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable

# Changes to these files/directories can alter the CI contract or dependency
# graph and therefore require the complete validation set.
FULL_PATHS = {
    ".github/workflows/",
    ".github/actions/",
    "pyproject.toml",
    "pytest.ini",
    "tox.ini",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "package.json",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain",
    "rust-toolchain.toml",
    ".gitmodules",
    "node_modules/",
    ".venv/",
    "venv/",
    "build/",
    "dist/",
    "downloads/",
    EXCLUDED_PATHS =
    "external/",
    "vendor/",
}

PYTHON_SUFFIXES = {".py", ".pyi"}
NODE_SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}
RUST_SUFFIXES = {".rs"}


def _normalize(path: str) -> str:
    value = str(path).replace("\\", "/").lstrip("./")
    return str(PurePosixPath(value))


def _is_excluded(path: str) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def _requires_full(path: str) -> bool:
    if path in FULL_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in FULL_PATHS if prefix.endswith("/"))


def scope(changed_paths: Iterable[str]) -> dict[str, object]:
    """Return deterministic CI lanes for *changed_paths*.

    The returned lists contain normalized repository-relative paths. Vendor and
    generated/external trees are excluded before lane selection. Any dependency,
    workflow, or build-contract change sets ``full`` to True.
    """
    normalized = sorted({_normalize(path) for path in changed_paths if str(path).strip()})
    changed = [path for path in normalized if not _is_excluded(path)]

    result: dict[str, object] = {
        "changed": changed,
        "python": [],
        "node": [],
        "rust": [],
        "full": False,
    }

    python: list[str] = []
    node: list[str] = []
    rust: list[str] = []

    for path in changed:
        if _requires_full(path):
            result["full"] = True

        suffix = PurePosixPath(path).suffix.lower()
        if suffix in PYTHON_SUFFIXES:
            python.append(path)
        elif suffix in NODE_SUFFIXES:
            node.append(path)
        elif suffix in RUST_SUFFIXES:
            rust.append(path)

    result["python"] = python
    result["node"] = node
    result["rust"] = rust
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Classify changed files into CI lanes")
    parser.add_argument("paths", nargs="*", help="repository-relative changed paths")
    args = parser.parse_args()

    import json
    print(json.dumps(scope(args.paths), indent=2, sort_keys=True))
