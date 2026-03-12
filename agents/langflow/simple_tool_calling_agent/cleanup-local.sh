#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DIR="$SCRIPT_DIR/local"

cd "$LOCAL_DIR"

if [ "${1:-}" = "--force" ]; then
  echo "Stopping services and removing all data..."
  # Stop containerized services
  podman-compose down --remove-orphans -v -t 5 2>/dev/null || true
  # Force kill and remove any lingering containers from this compose project
  for c in $(podman ps -a --filter "label=io.podman.compose.project=local" -q 2>/dev/null); do
    podman rm -f "$c" 2>/dev/null || true
  done
  # Remove project volumes
  for v in $(podman volume ls --filter "label=io.podman.compose.project=local" -q 2>/dev/null); do
    podman volume rm -f "$v" 2>/dev/null || true
  done
  # Remove project network
  podman network rm local_default 2>/dev/null || true
  # Stop native Ollama
  pkill -f "ollama serve" 2>/dev/null || true
  # Clean up config
  rm -f "$LOCAL_DIR/.ollama-enabled"
  rm -f "$LOCAL_DIR/.env"
  echo "Done. All services stopped and data removed."
else
  echo "Stopping services (data preserved)..."
  podman-compose down --remove-orphans 2>/dev/null || true
  # Stop native Ollama
  pkill -f "ollama serve" 2>/dev/null || true
  echo "Done. Run './deploy-local.sh' to start again."
fi
