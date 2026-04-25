#!/bin/bash
# Container runtime detection shim.
#
# Usage: source scripts/container-runtime.sh
#
# Exports:
#   CONTAINER_RUNTIME   # "docker" or "podman"
#   COMPOSE_CMD         # "docker compose" or "podman-compose"
#
# Set PREFER_PODMAN=1 to pick Podman when both are available.

if command -v podman >/dev/null 2>&1 && { [ "${PREFER_PODMAN:-0}" = "1" ] || ! command -v docker >/dev/null 2>&1; }; then
    export CONTAINER_RUNTIME="podman"
    if command -v podman-compose >/dev/null 2>&1; then
        export COMPOSE_CMD="podman-compose"
    else
        echo "⚠ podman detected but podman-compose is missing. Install with: pip install podman-compose" >&2
        export COMPOSE_CMD="podman-compose"
    fi
elif command -v docker >/dev/null 2>&1; then
    export CONTAINER_RUNTIME="docker"
    if docker compose version >/dev/null 2>&1; then
        export COMPOSE_CMD="docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        export COMPOSE_CMD="docker-compose"
    else
        echo "⚠ docker detected but no compose plugin found" >&2
        export COMPOSE_CMD="docker compose"
    fi
else
    echo "✗ Neither docker nor podman is installed." >&2
    echo "  On Brev instances, Docker should be available by default." >&2
    echo "  On a laptop, install one of them:" >&2
    echo "    macOS:  brew install --cask docker   (or: brew install podman)" >&2
    echo "    Linux:  curl -fsSL https://get.docker.com | sh" >&2
    return 1 2>/dev/null || exit 1
fi

echo "  Container runtime: ${CONTAINER_RUNTIME} (compose: ${COMPOSE_CMD})"
