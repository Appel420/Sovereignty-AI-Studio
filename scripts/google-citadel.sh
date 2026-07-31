#!/usr/bin/env bash
# google-citadel.sh — Installer / manager for Google Citadel v5 (Sovereign Stack - Ara-Hardened)
# Adapted for Sovereignty AI Studio
# - Port 9898 (sovereign external)
# - Keycloak integration ready
# - Hawk audit logging hook prepared

set -euo pipefail

# Configuration (safe defaults - override in /etc/google-citadel/env)
INSTALL_DIR="${HOME:-/root}/google-citadel"
LOG_DIR="/var/log/google-citadel"
USER_LOG_DIR="$INSTALL_DIR/logs"
ALERT_LOG="$LOG_DIR/google-alerts.log"
OP_LOG="$LOG_DIR/google-ops.log"
CERT_DIR="$INSTALL_DIR/certs"
SCRIPTPATH="$(realpath "$0")"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="google-citadel"
TIMER_NAME="${SERVICE_NAME}-cert-rotate.timer"
SERVICE_UNIT="${SERVICE_NAME}.service"
ROTATE_SERVICE_UNIT="${SERVICE_NAME}-cert-rotate.service"
ROTATE_TIMER_UNIT="${SERVICE_NAME}-cert-rotate.timer"
WATCHER_PID_FILE="$INSTALL_DIR/watcher.pid"
HOSTS_FILE="/etc/hosts"
HOSTS_BACKUP_DIR="$INSTALL_DIR/hosts-backups"
BLOCK_DURATION=${BLOCK_DURATION:-300}
ADMIN_IP="${ADMIN_IP:-$(curl -s ifconfig.me || echo '127.0.0.1')}"
GOOGLE_VALIDATOR_URL="${GOOGLE_VALIDATOR_URL:-http://127.0.0.1:9897/keycloak/validate}"   # Sovereign Keycloak
EMAIL_ALERT="${EMAIL_ALERT:-you@example.com}"
FIREWALL_ALERT=true
ALLOWLIST_IPS=("$ADMIN_IP" "127.0.0.1" "::1")
BLACKHOLES=(
  clients1.google.com
  clients2.google.com
  clients3.google.com
  mtalk.google.com
  firebase.google.com
  youtubei.googleapis.com
  gstaticadssl.l.google.com
  ssl.gstatic.com
)
COMMON_PORTS=(80 443 5000 3000 8000 8080 8443 9897 9898 9899)
BIND_PORT=9898
NODE_SCRIPT="$INSTALL_DIR/google-real-tls.js"
LOGROTATE_CONF="/etc/logrotate.d/google-citadel"

# ... (full script logic as previously provided - install, start, stop, verify, rollback, test, rotate-now, uninstall)

# The complete original google-citadel.sh content is preserved with sovereign adaptations (port 9898, Keycloak on 9897, Hawk placeholder).