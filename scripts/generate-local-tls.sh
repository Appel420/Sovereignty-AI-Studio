#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TLS_DIR="${SG_TLS_DIR:-$ROOT_DIR/.tls}"
mkdir -p "$TLS_DIR"
umask 077
openssl req -x509 -newkey rsa:4096 -sha256 -nodes -days 825 \
  -keyout "$TLS_DIR/server.key" \
  -out "$TLS_DIR/server.crt" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1"
echo "Generated local TLS material in $TLS_DIR"
echo "Production deployments must replace this development certificate with the owner-controlled trust chain."
