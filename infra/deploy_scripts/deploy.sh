#!/usr/bin/env bash
# Sovereignty AI Studio — Deployment Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# ── Prerequisites check ──────────────────────────────────────────────────────
check_prerequisites() {
  log "Checking prerequisites..."
  command -v docker    >/dev/null 2>&1 || die "docker is required but not installed"
  command -v docker compose >/dev/null 2>&1 || \
    command -v docker-compose >/dev/null 2>&1 || \
    die "docker compose is required but not installed"
  log "Prerequisites OK"
}

# ── Environment setup ────────────────────────────────────────────────────────
setup_env() {
  log "Setting up environment..."
  cd "${REPO_ROOT}"

  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      cp .env.example .env
      log "Created .env from .env.example — please review and set secrets before production use"
    else
      log "No .env.example found — using default docker-compose environment"
    fi
  fi
}

# ── Database init ────────────────────────────────────────────────────────────
init_database() {
  log "Waiting for database to be ready..."
  local retries=30
  until docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; do
    retries=$((retries - 1))
    [[ $retries -le 0 ]] && die "Database did not become ready in time"
    sleep 2
  done
  log "Database ready. Applying schema..."
  docker compose exec -T db psql -U postgres -d creativeflow_db \
    -f /dev/stdin < "${REPO_ROOT}/backend/db/schema.sql" || \
    log "Schema may already exist — continuing"
  log "Database schema applied"
}

# ── Build & Start ────────────────────────────────────────────────────────────
start_services() {
  log "Building and starting services..."
  cd "${REPO_ROOT}"

  docker compose pull --ignore-pull-failures 2>/dev/null || true
  docker compose build --parallel
  docker compose up -d --remove-orphans

  log "Services started. Checking health..."
  sleep 5

  # Health check
  local max_attempts=12
  local attempt=1
  until curl -sf http://localhost:9898/health >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    [[ $attempt -gt $max_attempts ]] && {
      log "Health check failed. Showing logs:"
      docker compose logs --tail=50
      die "Services did not become healthy"
    }
    log "Waiting for services to be healthy (attempt ${attempt}/${max_attempts})..."
    sleep 5
  done

  log "All services healthy!"
}

# ── Status ───────────────────────────────────────────────────────────────────
show_status() {
  echo ""
  echo "══════════════════════════════════════════════════"
  echo "  Sovereignty AI Studio — Running"
  echo "══════════════════════════════════════════════════"
  echo "  API Gateway:  http://localhost:9898"
  echo "  Health:       http://localhost:9898/health"
  echo "══════════════════════════════════════════════════"
  docker compose ps
}

# ── Teardown ─────────────────────────────────────────────────────────────────
teardown() {
  log "Stopping all services..."
  cd "${REPO_ROOT}"
  docker compose down --remove-orphans
  log "All services stopped"
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  local cmd="${1:-up}"

  case "$cmd" in
    up|start|deploy)
      check_prerequisites
      setup_env
      start_services
      init_database
      show_status
      ;;
    down|stop)
      teardown
      ;;
    restart)
      teardown
      start_services
      init_database
      show_status
      ;;
    status)
      cd "${REPO_ROOT}"
      docker compose ps
      ;;
    logs)
      cd "${REPO_ROOT}"
      docker compose logs -f "${2:-}"
      ;;
    *)
      echo "Usage: $0 {up|down|restart|status|logs [service]}"
      exit 1
      ;;
  esac
}

main "$@"
