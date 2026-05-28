#!/usr/bin/env bash
# Run on the server after git pull (also called from GitHub Actions via SSH).
set -euo pipefail

REPO_DIR="${DEPLOY_PATH:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose.yml}"
BRANCH="${DEPLOY_BRANCH:-main}"

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"; }

cd "$REPO_DIR"
log "Deploy started in $REPO_DIR (branch: $BRANCH)"

if [[ ! -f .env ]]; then
  log "ERROR: .env not found. Copy .env.example to .env and configure secrets."
  exit 1
fi

if [[ ! -d .git ]]; then
  log "ERROR: $REPO_DIR is not a git repository."
  exit 1
fi

log "Fetching latest code..."
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

export COMPOSE_FILE

log "Building images..."
docker compose -f "$COMPOSE_FILE" build

log "Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

log "Waiting for API container..."
for i in {1..30}; do
  if docker compose -f "$COMPOSE_FILE" ps api --status running -q 2>/dev/null | grep -q .; then
    break
  fi
  sleep 2
done

log "Running database migrations..."
docker compose -f "$COMPOSE_FILE" exec -T api alembic upgrade head

log "Pruning unused Docker images..."
docker image prune -f >/dev/null 2>&1 || true

log "Deploy finished successfully."
docker compose -f "$COMPOSE_FILE" ps
