#!/usr/bin/env bash
# Device-local Sovereignty family-tree initializer. No network or provider calls.
set -euo pipefail

ROOT="${SOVEREIGN_STATE_ROOT:-$HOME/Admin/On Device Memory Storage}"

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

cat > "$ROOT/provider-registry.json" <<'JSON'
{
  "version": "1.0.0",
  "owner": "device-owner",
  "storage_root": "device-local",
  "network": "disabled",
  "external_memory": "disabled",
  "providers": [
    {"id":"local.github_copilot","name":"GitHub Copilot","role":"implementation_review","storage":"GitHub Copilot Local Storage","network":false},
    {"id":"local.claude","name":"Anthropic Claude Fable","role":"long_context_analysis","storage":"Anthropic Claude Fable Local Storage","network":false},
    {"id":"local.openai_codex","name":"OpenAI ChatGPT Codex","role":"reasoning_and_coding","storage":"OpenAI ChatGPT Codex Local Storage","network":false},
    {"id":"local.grok","name":"X.AI Grok / Ara","role":"adversarial_review","storage":"X.AI Grok Local Storage","network":false},
    {"id":"local.duckai","name":"DuckAI","role":"privacy_research","storage":"DuckAI Local Storage","network":false},
    {"id":"local.devassist420","name":"DevAssist420","role":"hybrid_coordination","storage":"DevAssist420 Local Hybrid Collaboration","network":false},
    {"id":"local.sovereignty_ai","name":"Sovereignty AI","role":"owner_visible_router_and_council","storage":"Sovereignty AI","network":false}
  ],
  "wake_word": {
    "primary": "hey ara",
    "alternatives": ["on sovereignty ai", "devassist420"],
    "recognition": "local_engine_required",
    "remote_recognition": false,
    "status": "not_configured"
  }
}
JSON

cat > "$ROOT/audit/README.txt" <<'EOF'
All provider actions must record:
who, what, when, where, why, how,
authorization, memory_loaded, network_accessed,
files_changed, and result.

Network is disabled by default. Remote listening is disabled.
EOF

printf 'Created local Sovereignty family tree at: %s\n' "$ROOT"
