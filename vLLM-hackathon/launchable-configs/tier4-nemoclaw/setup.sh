#!/bin/bash
# =============================================================================
# TOA vLLM/LLM-D Hackathon — Tier 4: Agentic Edge (NVIDIA GPU Prize / Track 5)
# Brev Launchable Setup Script
# GPU: 1x A100 80GB (preferred) or 1x H100
# Stack: NemoClaw + OpenShell + vLLM + Nemotron-compatible tools
# =============================================================================

set -euo pipefail

echo "============================================="
echo "  TOA Hackathon — Agentic Edge (Track 5)"
echo "  Setting up NemoClaw + vLLM environment..."
echo "============================================="

# --- System basics ---
sudo apt-get update -qq
sudo apt-get install -y -qq git curl wget jq htop tmux tree ca-certificates gnupg lsb-release

# --- Node.js 20+ (required by NemoClaw) ---
if ! command -v node &> /dev/null || [ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt 20 ]; then
    echo "[1/8] Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# --- Docker (required by OpenShell sandbox) ---
if ! command -v docker &> /dev/null; then
    echo "[2/8] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
fi

# --- Python + vLLM + agent deps ---
echo "[3/8] Installing Python packages..."
pip install --upgrade pip --break-system-packages -q
pip install --break-system-packages -q \
    vllm \
    torch \
    transformers \
    huggingface_hub \
    httpx \
    pydantic \
    gradio \
    rich \
    jupyter

# --- Download Llama 3.1 8B (agent backbone) ---
echo "[4/8] Downloading Llama 3.1 8B Instruct (agent backbone)..."
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'meta-llama/Llama-3.1-8B-Instruct',
    local_dir='/models/llama-3.1-8b-instruct',
    ignore_patterns=['*.pth', 'original/**']
)
"

# --- Optionally download Nemotron-3-Nano-30B for comparison ---
echo "[5/8] (Optional) Pre-caching Nemotron-3-Nano for profile comparison..."
# Attendees can uncomment this if they have the bandwidth.
# python3 -c "
# from huggingface_hub import snapshot_download
# snapshot_download(
#     'nvidia/Nemotron-3-Nano-30B-A3B',
#     local_dir='/models/nemotron-3-nano-30b'
# )
# "

# --- Install NemoClaw ---
echo "[6/8] Installing NemoClaw..."
curl -fsSL https://nvidia.com/nemoclaw.sh | bash

# --- vLLM launch script ---
echo "[7/8] Setting up vLLM launch script..."
cat > /workspace/start_vllm_server.sh << 'VLLM_SCRIPT'
#!/bin/bash
# Start vLLM serving the agent backbone.
echo "Starting vLLM with Llama 3.1 8B for NemoClaw agent..."
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-8b-instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.85 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --dtype auto
VLLM_SCRIPT
chmod +x /workspace/start_vllm_server.sh

# --- Onboarding helper ---
cat > /workspace/onboard_nemoclaw.sh << 'ONBOARD'
#!/bin/bash
# One-shot NemoClaw onboarding pointed at the local vLLM server.
NEMOCLAW_PROVIDER=custom \
NEMOCLAW_ENDPOINT_URL=http://localhost:8000/v1 \
NEMOCLAW_MODEL=/models/llama-3.1-8b-instruct \
COMPATIBLE_API_KEY=dummy \
NEMOCLAW_PREFERRED_API=openai-completions \
nemoclaw onboard --non-interactive --name agentic-edge
ONBOARD
chmod +x /workspace/onboard_nemoclaw.sh

# --- Clone demo repo contents (agent scaffold) ---
echo "[8/8] Staging agent scaffold..."
mkdir -p /workspace/nemoclaw-agent
# The attendee repo's demo/nemoclaw-agent/ will be mounted or cloned in.
# For auto-clone, uncomment:
# git clone --depth 1 https://github.com/holzerjm/vLLM-hackathon.git /tmp/hack
# cp -r /tmp/hack/demo/nemoclaw-agent/* /workspace/nemoclaw-agent/

# --- Validation ---
cat > /workspace/test_setup.sh << 'VALIDATE'
#!/bin/bash
echo "============================================="
echo "  NemoClaw Agentic Edge — Validation"
echo "============================================="
PASS=0; FAIL=0

check() {
    if eval "$2" > /dev/null 2>&1; then
        echo "  ✓ $1"; ((PASS++))
    else
        echo "  ✗ $1"; ((FAIL++))
    fi
}

check "NVIDIA GPU detected"      "nvidia-smi"
check "CUDA available"           "python3 -c 'import torch; assert torch.cuda.is_available()'"
check "vLLM installed"           "python3 -c 'import vllm'"
check "Docker running"           "docker ps"
check "Node.js 20+"              "node -v | grep -E 'v(2[0-9]|[3-9][0-9])'"
check "NemoClaw installed"       "command -v nemoclaw"
check "Model weights present"    "test -d /models/llama-3.1-8b-instruct"

echo "---------------------------------------------"
echo "  Results: $PASS passed, $FAIL failed"
echo "============================================="
VALIDATE
chmod +x /workspace/test_setup.sh

echo ""
echo "============================================="
echo "  ✅ Agentic Edge environment ready!"
echo ""
echo "  Quick start:"
echo "    1. bash /workspace/test_setup.sh"
echo "    2. bash /workspace/start_vllm_server.sh    (in one tmux pane)"
echo "    3. bash /workspace/onboard_nemoclaw.sh      (in another)"
echo "    4. nemoclaw agentic-edge connect"
echo "    5. openclaw tui"
echo ""
echo "  Demo scaffold: /workspace/nemoclaw-agent/"
echo "  (clone your hackathon repo there or copy from demo/nemoclaw-agent/)"
echo "============================================="
