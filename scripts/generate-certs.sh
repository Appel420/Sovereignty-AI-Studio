#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Generate self-signed TLS certificates for local development
# Usage: ./scripts/generate-certs.sh [output_dir]
# ─────────────────────────────────────────────────────────────
set -euo pipefail

CERT_DIR="${1:-./certs}"
DAYS="${TLS_DAYS:-365}"
CN="${TLS_CN:-localhost}"

mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
  echo "⚠️  Certificates already exist in $CERT_DIR — skipping."
  echo "   Delete them first if you want to regenerate."
  exit 0
fi

echo "🔐 Generating self-signed TLS certificate..."
echo "   Output  : $CERT_DIR"
echo "   CN      : $CN"
echo "   Validity: $DAYS days"

openssl req -x509 -newkey rsa:2048 -nodes \
  -days "$DAYS" \
  -keyout "$CERT_DIR/key.pem" \
  -out "$CERT_DIR/cert.pem" \
  -subj "/CN=$CN" \
  2>/dev/null

echo "✅ Certificates generated:"
echo "   cert: $CERT_DIR/cert.pem"
echo "   key : $CERT_DIR/key.pem"
echo ""
echo "Add to your .env:"
echo "   TLS_CERT=$CERT_DIR/cert.pem"
echo "   TLS_KEY=$CERT_DIR/key.pem"
