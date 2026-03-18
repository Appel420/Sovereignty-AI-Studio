#!/usr/bin/env bash
# tls_rotate.sh — Auto-generates and rotates self-signed TLS certificates
# for the Sovereignty AI Studio gateway.
#
# Usage:
#   ./scripts/tls_rotate.sh [cert-dir]
#
# Environment:
#   TLS_DIR      — Directory to store certs (default: /etc/sovereignty/tls)
#   TLS_DAYS     — Certificate validity in days (default: 90)
#   TLS_DOMAIN   — Common Name / Subject Alt Name (default: sovereignty.local)
#   LOG_FILE     — Path to rotation log (default: /var/log/tls_rotate.log)

set -euo pipefail

TLS_DIR="${TLS_DIR:-/etc/sovereignty/tls}"
TLS_DAYS="${TLS_DAYS:-90}"
TLS_DOMAIN="${TLS_DOMAIN:-sovereignty.local}"
LOG_FILE="${LOG_FILE:-/var/log/tls_rotate.log}"
TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Allow caller to override cert dir via positional argument
if [[ $# -ge 1 ]]; then
  TLS_DIR="$1"
fi

log() {
  echo "[${TIMESTAMP}] $*" | tee -a "${LOG_FILE}"
}

# Ensure output directory exists
mkdir -p "${TLS_DIR}"

CERT="${TLS_DIR}/server.crt"
KEY="${TLS_DIR}/server.key"
BACKUP_DIR="${TLS_DIR}/backup-${TIMESTAMP//:/}"

# Back up existing certs if present
if [[ -f "${CERT}" || -f "${KEY}" ]]; then
  mkdir -p "${BACKUP_DIR}"
  [[ -f "${CERT}" ]] && cp "${CERT}" "${BACKUP_DIR}/server.crt"
  [[ -f "${KEY}" ]]  && cp "${KEY}"  "${BACKUP_DIR}/server.key"
  log "Backed up existing certificates to ${BACKUP_DIR}"
fi

# Generate new self-signed certificate
openssl req -x509 -nodes \
  -newkey rsa:4096 \
  -keyout "${KEY}" \
  -out    "${CERT}" \
  -days   "${TLS_DAYS}" \
  -subj   "/CN=${TLS_DOMAIN}/O=SovereigntyAI/C=US" \
  -addext "subjectAltName=DNS:${TLS_DOMAIN},DNS:localhost,IP:127.0.0.1" \
  2>/dev/null

chmod 600 "${KEY}"
chmod 644 "${CERT}"

EXPIRY=$(openssl x509 -noout -enddate -in "${CERT}" | cut -d= -f2)
log "TLS certificate rotated successfully"
log "  Domain   : ${TLS_DOMAIN}"
log "  Cert     : ${CERT}"
log "  Key      : ${KEY}"
log "  Expires  : ${EXPIRY}"
log "  Valid for: ${TLS_DAYS} days"

# Signal running services to reload (if applicable)
if command -v systemctl &>/dev/null; then
  for svc in nginx node-bridge sovereignty-gateway; do
    if systemctl is-active --quiet "${svc}" 2>/dev/null; then
      systemctl reload "${svc}" && log "Reloaded ${svc}"
    fi
  done
fi

log "TLS rotation complete"
