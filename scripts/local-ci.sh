#!/usr/bin/env bash
Deterministic CI supporting three modes: Local-First, Local-Hybrid, and Fully-Online.
Owner policy: self-hosted Linux arm64. Fail closed. Delete nothing.
set -Eeuo pipefail

ROOTDIR="$(CDPATH= cd -- "$(dirname -- "${BASHSOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

Default: Local-First
export SGNETWORKMODE="offline"
export SGLOCALFIRST="1"
export SGEXTERNALFEEDS="disabled"
export CLOUD_FIRST="false"

Local-Hybrid mode (enable selective cloud access)
export SGLOCALHYBRID="0"

Fully-Online mode (overrides local settings)
export SGFULLYONLINE="0"

Package manager configurations
export PIPNOINDEX="1"
export PIPNOINPUT="1"
export PIPDISABLEPIPVERSIONCHECK="1"
export npmconfigoffline="true"
export npmconfigaudit="false"
export npmconfigfund="false"
export NO_PROXY="*"
export no_proxy="*"

Enforce local-first shell-only gate before handing off to Python runner.
exec "${PYTHON:-python3}" scripts/run-local-ci.py "$@"
