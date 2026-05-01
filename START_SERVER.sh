#!/bin/bash
# ═══════════════════════════════════════════════════════
# SUPERGROK PORT 9897 BRIDGE STARTUP
# Zero Meta · Zero Google · Zero LLaMA · Zero Ollama
# All AI: DDG Privacy Bridge + Piper TTS (local only)
# ═══════════════════════════════════════════════════════

# Set your Piper model path (download from github.com/rhasspy/piper/releases)
export PIPER_MODEL="${PIPER_MODEL:-./models/en_US-lessac-medium.onnx}"
export PIPER_DIR="${PIPER_DIR:-./piper-tts}"

# Optional: your self-signed TLS cert
export TLS_CERT="${TLS_CERT:-}"
export TLS_KEY="${TLS_KEY:-}"

echo "Starting SuperGrok bridge on port 9897..."
echo "Piper model: $PIPER_MODEL"
echo "Network: localhost only — nothing leaves device without user permission"
echo ""

SG_PORT=9897 python bridge.py
