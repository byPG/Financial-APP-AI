#!/usr/bin/env bash
# Build (if needed) and run the Finance App Docker container.
# See planning/PLAN.md Section 11.
#
# Usage:
#   ./scripts/start_mac.sh            # build only if the image doesn't exist yet
#   ./scripts/start_mac.sh --build    # force a rebuild
#
# Idempotent: safe to run again while the container is already running —
# it detects the existing container and leaves it running rather than erroring.

set -euo pipefail

IMAGE_NAME="finance-app"
CONTAINER_NAME="finance-app"
PORT="8000"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

FORCE_BUILD="false"
if [[ "${1:-}" == "--build" ]]; then
  FORCE_BUILD="true"
fi

if [[ ! -f ".env" ]]; then
  echo "Warning: .env not found in project root. Copy .env.example to .env and fill in OPENROUTER_API_KEY." >&2
fi

mkdir -p "${PROJECT_ROOT}/db"

# Build the image if it doesn't exist yet, or if --build was passed.
IMAGE_EXISTS="$(docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1 && echo "true" || echo "false")"
if [[ "${FORCE_BUILD}" == "true" || "${IMAGE_EXISTS}" == "false" ]]; then
  echo "Building Docker image '${IMAGE_NAME}'..."
  docker build -t "${IMAGE_NAME}" -f Dockerfile .
else
  echo "Image '${IMAGE_NAME}' already exists, skipping build (use --build to force)."
fi

# Idempotent container handling: if a container with this name is already
# running, leave it alone. If it exists but is stopped, remove it so we can
# start fresh. If it doesn't exist, just run it.
EXISTING_STATE="$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || echo "missing")"

if [[ "${EXISTING_STATE}" == "true" ]]; then
  echo "Container '${CONTAINER_NAME}' is already running."
elif [[ "${EXISTING_STATE}" == "false" ]]; then
  echo "Removing stopped container '${CONTAINER_NAME}'..."
  docker rm "${CONTAINER_NAME}" >/dev/null
  echo "Starting container '${CONTAINER_NAME}'..."
  docker run -d \
    --name "${CONTAINER_NAME}" \
    -p "${PORT}:8000" \
    -v "${PROJECT_ROOT}/db:/app/db" \
    --env-file "${PROJECT_ROOT}/.env" \
    "${IMAGE_NAME}"
else
  echo "Starting container '${CONTAINER_NAME}'..."
  docker run -d \
    --name "${CONTAINER_NAME}" \
    -p "${PORT}:8000" \
    -v "${PROJECT_ROOT}/db:/app/db" \
    --env-file "${PROJECT_ROOT}/.env" \
    "${IMAGE_NAME}"
fi

URL="http://localhost:${PORT}"
echo "Finance App is available at ${URL}"

# Best-effort browser open; never fail the script if `open` is unavailable.
if command -v open >/dev/null 2>&1; then
  open "${URL}" || true
fi
