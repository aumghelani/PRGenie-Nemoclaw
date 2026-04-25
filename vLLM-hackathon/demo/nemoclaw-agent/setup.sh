#!/bin/bash
# =============================================================================
# Track 5 — NVIDIA GPU Prize: Agentic Edge powered by NemoClaw
# Installs NemoClaw and wires it up to a local vLLM server for inference.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================="
echo "  Track 5 — NemoClaw Agentic Edge Demo"
echo "============================================="

# --- System basics ---
# NemoClaw specifically requires Docker — its OpenShell sandbox talks to the
# Docker socket directly. Podman is not supported for this track.
# See docs/PODMAN-NOTES.md for the full compatibility matrix.
if ! command -v docker &> /dev/null; then
    echo "✗ Docker is required for NemoClaw (OpenShell sandbox dependency)."
    echo ""
    if command -v podman &> /dev/null; then
        echo "  Podman is installed but NemoClaw does not support it. See:"
        echo "  docs/PODMAN-NOTES.md  (NemoClaw section)"
    fi
    echo "  Install Docker:"
    echo "    https://docs.docker.com/engine/install/ubuntu/"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# --- Install NemoClaw ---
echo "[1/4] Installing NemoClaw..."
if ! command -v nemoclaw &> /dev/null; then
    curl -fsSL https://nvidia.com/nemoclaw.sh | bash
fi

# --- Verify vLLM is running ---
echo "[2/4] Checking local vLLM server..."
if ! curl -s http://localhost:8000/v1/models &> /dev/null; then
    echo "  vLLM not running. Start it first:"
    echo "  bash /workspace/start_vllm_server.sh"
    echo "  (or any other vLLM launch script you prefer)"
    exit 1
fi
echo "  vLLM detected at http://localhost:8000/v1"

# --- Onboard NemoClaw with the vLLM profile ---
echo "[3/4] Onboarding NemoClaw with vLLM inference profile..."
NEMOCLAW_PROVIDER=custom \
NEMOCLAW_ENDPOINT_URL=http://localhost:8000/v1 \
NEMOCLAW_MODEL=/models/llama-3.1-8b-instruct \
COMPATIBLE_API_KEY=dummy \
NEMOCLAW_PREFERRED_API=openai-completions \
nemoclaw onboard --non-interactive --name agentic-edge

# --- Copy blueprint + tools into the sandbox ---
echo "[4/4] Installing agent scaffold..."
SANDBOX_WORKSPACE="$HOME/.nemoclaw/sandboxes/agentic-edge/workspace"
mkdir -p "$SANDBOX_WORKSPACE"
cp -r "$SCRIPT_DIR"/tools "$SANDBOX_WORKSPACE/"
cp "$SCRIPT_DIR/customer_support_agent.py" "$SANDBOX_WORKSPACE/"
cp "$SCRIPT_DIR/blueprint.yaml" "$SANDBOX_WORKSPACE/"

echo ""
echo "============================================="
echo "  ✅ NemoClaw Agentic Edge ready!"
echo ""
echo "  Connect to the sandbox:"
echo "    nemoclaw agentic-edge connect"
echo ""
echo "  Then start the agent TUI:"
echo "    openclaw tui"
echo ""
echo "  Or run the customer support agent:"
echo "    python3 /workspace/customer_support_agent.py"
echo ""
echo "  Benchmark the agent loop (Deep Tech tier):"
echo "    python3 /workspace/benchmarks/latency-test.py"
echo "============================================="
