#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOVEREIGN_STATE_ROOT:-$HOME/Admin/On Device Memory Storage}"

# Fail closed on empty, filesystem-root, relative, or traversal-containing paths.
if [[ -z "${ROOT:-}" || "$ROOT" == "/" || "$ROOT" != /* || "$ROOT" == *"/../"* || "$ROOT" == ../* || "$ROOT" == */.. ]]; then
  echo "Refusing unsafe ROOT path: ${ROOT:-<empty>}" >&2
  exit 1
fi

mkdir -p \
  "$ROOT/GitHub Copilot Local Storage" \
  "$ROOT/Anthropic Claude Fable Local Storage" \
  "$ROOT/OpenAI ChatGPT Codex Local Storage" \
  "$ROOT/X.AI Grok Local Storage" \
  "$ROOT/DuckAI Local Storage" \
  "$ROOT/DevAssist420 Local Hybrid Collaboration" \
  "$ROOT/Sovereignty AI" \
  "$ROOT/Router/Council/Claude" \
  "$ROOT/Router/Council/Ara-Grok" \
  "$ROOT/Router/Council/ChatGPT-Codex" \
  "$ROOT/Router/Council/DevAssist420" \
  "$ROOT/Router/Council/DuckAI" \
  "$ROOT/Router/Council/GitHub Copilot" \
  "$ROOT/Router/Council/Sovereignty AI" \
  "$ROOT/audit" \
  "$ROOT/hybrid"

cat > "$ROOT/audit/README.txt" <<'EOF'
All provider actions must record:
who, what, when, where, why, how,
authorization, memory_loaded, network_accessed,
files_changed, and result.
EOF

echo "Initialization complete. Local Sovereignty family tree created."
