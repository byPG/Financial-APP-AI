#!/usr/bin/env bash
# Stop and remove the Finance App Docker container.
# Does NOT remove the bind-mounted db/ data — that persists on the host.
# See planning/PLAN.md Section 11.
#
# Idempotent: safe to run when nothing is running.

set -euo pipefail

CONTAINER_NAME="finance-app"

if docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
  echo "Stopping container '${CONTAINER_NAME}'..."
  docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  echo "Removing container '${CONTAINER_NAME}'..."
  docker rm "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  echo "Container '${CONTAINER_NAME}' stopped and removed. Data in db/ is preserved."
else
  echo "Container '${CONTAINER_NAME}' is not present. Nothing to do."
fi
