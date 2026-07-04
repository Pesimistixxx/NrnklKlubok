#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Stop and remove containers + volumes"
docker compose down -v --remove-orphans

echo "==> Remove project images"
docker images --format '{{.Repository}}:{{.Tag}}' | grep '^mkg-local-' | xargs -r docker rmi -f || true

echo "==> Clear build cache"
docker builder prune -af

echo "==> Build from scratch"
docker compose build --no-cache

echo "==> Start"
docker compose up -d

echo "==> Wait for gateway"
sleep 5
docker compose ps
docker compose logs gateway --tail 25

echo "==> Import check"
docker compose exec -T gateway python -c "from mkg_core.embeddings import list_indexed_points; print('OK')"
