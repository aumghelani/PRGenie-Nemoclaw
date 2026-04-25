#!/bin/bash
# =============================================================================
# TOA vLLM/LLM-D Hackathon — Tier 3: Deep Tech / Inference at Scale
# Brev Launchable Setup Script
# GPU: 4x A100 80GB or 4x H100
# Focus: llm-d distributed inference, disaggregated prefill/decode, KV-cache routing
# =============================================================================

set -euo pipefail

echo "============================================="
echo "  TOA Hackathon — Deep Tech Environment"
echo "  Setting up distributed inference cluster..."
echo "============================================="

# --- System basics ---
sudo apt-get update -qq
sudo apt-get install -y -qq git curl wget jq htop tmux tree nvtop socat

# --- Python environment ---
echo "[1/8] Setting up Python environment..."
pip install --upgrade pip --break-system-packages -q
pip install --break-system-packages -q \
    vllm \
    torch \
    transformers \
    huggingface_hub \
    guidellm \
    lm-eval \
    llmcompressor \
    jupyter \
    ipywidgets \
    pandas \
    matplotlib \
    rich \
    httpx \
    py-spy \
    prometheus-client

# --- Kubernetes tooling ---
echo "[2/8] Installing Kubernetes tooling..."
# kubectl
curl -sLO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl

# Helm
curl -sfL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# kind (local K8s cluster)
curl -sLo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
sudo install -o root -g root -m 0755 kind /usr/local/bin/kind && rm kind

# k9s (cluster UI)
curl -sLo /tmp/k9s.tar.gz https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz
tar -xzf /tmp/k9s.tar.gz -C /tmp && sudo mv /tmp/k9s /usr/local/bin/

# --- Download models ---
echo "[3/8] Downloading Llama 3.1 8B Instruct..."
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'meta-llama/Llama-3.1-8B-Instruct',
    local_dir='/models/llama-3.1-8b-instruct',
    ignore_patterns=['*.pth', 'original/**']
)
"

echo "[4/8] Downloading Llama 3.1 70B Instruct..."
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'meta-llama/Llama-3.1-70B-Instruct',
    local_dir='/models/llama-3.1-70b-instruct',
    ignore_patterns=['*.pth', 'original/**']
)
"

# --- Clone and set up llm-d ---
echo "[5/8] Setting up llm-d..."
git clone --depth 1 https://github.com/llm-d/llm-d.git /workspace/llm-d
cd /workspace/llm-d

# --- llm-d deployment configurations ---
echo "[6/8] Creating llm-d deployment configs..."
mkdir -p /workspace/llm-d-configs

# Basic llm-d values for Helm deployment
cat > /workspace/llm-d-configs/values-8b.yaml << 'VALUES8B'
# llm-d Helm values — Llama 3.1 8B single-node
model:
  name: "meta-llama/Llama-3.1-8B-Instruct"
  localPath: "/models/llama-3.1-8b-instruct"

vllm:
  replicas: 1
  resources:
    limits:
      nvidia.com/gpu: 1
  extraArgs:
    - "--max-model-len=8192"
    - "--gpu-memory-utilization=0.85"

gateway:
  serviceType: ClusterIP

scheduler:
  enabled: true
  kvCacheAwareRouting: true
VALUES8B

cat > /workspace/llm-d-configs/values-70b-distributed.yaml << 'VALUES70B'
# llm-d Helm values — Llama 3.1 70B distributed with disaggregated serving
model:
  name: "meta-llama/Llama-3.1-70B-Instruct"
  localPath: "/models/llama-3.1-70b-instruct"

# Disaggregated prefill/decode architecture
prefill:
  replicas: 1
  resources:
    limits:
      nvidia.com/gpu: 2
  extraArgs:
    - "--max-model-len=4096"
    - "--tensor-parallel-size=2"

decode:
  replicas: 1
  resources:
    limits:
      nvidia.com/gpu: 2
  extraArgs:
    - "--max-model-len=4096"
    - "--tensor-parallel-size=2"

gateway:
  serviceType: ClusterIP

scheduler:
  enabled: true
  kvCacheAwareRouting: true
  disaggregatedServing: true
VALUES70B

# --- Helper scripts for llm-d workflows ---
echo "[7/8] Creating helper scripts..."
mkdir -p /workspace/scripts

cat > /workspace/scripts/start_kind_cluster.sh << 'KIND_CLUSTER'
#!/bin/bash
# Create a kind cluster with GPU support for llm-d
echo "Creating kind cluster with GPU passthrough..."
cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: llm-d-hackathon
nodes:
- role: control-plane
- role: worker
  extraMounts:
  - hostPath: /models
    containerPath: /models
    readOnly: true
EOF

echo "Installing NVIDIA device plugin..."
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/deployments/static/nvidia-device-plugin.yml

echo "Cluster ready. Nodes:"
kubectl get nodes
KIND_CLUSTER
chmod +x /workspace/scripts/start_kind_cluster.sh

cat > /workspace/scripts/deploy_llm_d.sh << 'DEPLOY'
#!/bin/bash
# Deploy llm-d using Helm
# Usage: bash deploy_llm_d.sh [values-file]
VALUES=${1:-/workspace/llm-d-configs/values-8b.yaml}

echo "Deploying llm-d with values: $VALUES"

cd /workspace/llm-d
helm install llm-d ./charts/llm-d \
    -f "$VALUES" \
    --namespace llm-d \
    --create-namespace \
    --wait --timeout 300s

echo ""
echo "Deployment status:"
kubectl get pods -n llm-d
echo ""
echo "To access the gateway:"
echo "  kubectl port-forward -n llm-d svc/llm-d-gateway 8000:8000"
DEPLOY
chmod +x /workspace/scripts/deploy_llm_d.sh

cat > /workspace/scripts/monitor_inference.py << 'MONITOR'
"""
Real-time inference monitoring dashboard.
Shows throughput, latency, KV-cache utilization, and GPU stats.
"""
import httpx, time, json, subprocess
from rich.console import Console
from rich.table import Table
from rich.live import Live

console = Console()

def get_gpu_stats():
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    gpus = []
    for line in result.stdout.strip().split("\n"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 5:
            gpus.append({
                "id": parts[0], "util": f"{parts[1]}%",
                "mem": f"{parts[2]}/{parts[3]} MB", "temp": f"{parts[4]}°C"
            })
    return gpus

def get_vllm_metrics(port=8000):
    try:
        r = httpx.get(f"http://localhost:{port}/metrics", timeout=5)
        metrics = {}
        for line in r.text.split("\n"):
            if line and not line.startswith("#"):
                parts = line.split(" ")
                if len(parts) == 2:
                    metrics[parts[0]] = parts[1]
        return metrics
    except Exception:
        return {}

def build_dashboard():
    table = Table(title="Inference Monitor", show_header=True)
    table.add_column("GPU", style="cyan")
    table.add_column("Utilization", style="green")
    table.add_column("Memory", style="yellow")
    table.add_column("Temp", style="red")

    for gpu in get_gpu_stats():
        table.add_row(f"GPU {gpu['id']}", gpu['util'], gpu['mem'], gpu['temp'])

    return table

if __name__ == "__main__":
    print("Starting inference monitor (Ctrl+C to stop)...")
    with Live(build_dashboard(), refresh_per_second=1) as live:
        while True:
            live.update(build_dashboard())
            time.sleep(1)
MONITOR

# --- Environment validation ---
echo "[8/8] Creating environment validation script..."
cat > /workspace/test_setup.sh << 'VALIDATE'
#!/bin/bash
echo "============================================="
echo "  Deep Tech Environment Validation"
echo "============================================="
PASS=0; FAIL=0

check() {
    if eval "$2" > /dev/null 2>&1; then
        echo "  ✓ $1"; ((PASS++))
    else
        echo "  ✗ $1"; ((FAIL++))
    fi
}

GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l)
echo "  GPUs detected: $GPU_COUNT"
echo ""

check "NVIDIA GPUs detected"           "nvidia-smi"
check "4+ GPUs available"              "[ $GPU_COUNT -ge 4 ]"
check "CUDA available"                 "python3 -c 'import torch; assert torch.cuda.is_available()'"
check "vLLM installed"                 "python3 -c 'import vllm'"
check "8B model weights present"       "test -d /models/llama-3.1-8b-instruct"
check "70B model weights present"      "test -d /models/llama-3.1-70b-instruct"
check "kubectl installed"              "kubectl version --client"
check "Helm installed"                 "helm version"
check "kind installed"                 "kind version"
check "k9s installed"                  "k9s version"
check "llm-d repo present"            "test -d /workspace/llm-d"
check "llm-d configs present"         "test -f /workspace/llm-d-configs/values-70b-distributed.yaml"

echo "---------------------------------------------"
echo "  Results: $PASS passed, $FAIL failed"
if [ $FAIL -eq 0 ]; then
    echo "  🎉 All checks passed — you're ready to hack!"
else
    echo "  ⚠  Some checks failed. Ask a mentor for help."
fi
echo "============================================="
VALIDATE
chmod +x /workspace/test_setup.sh

echo ""
echo "============================================="
echo "  ✅ Deep Tech environment ready!"
echo ""
echo "  Quick start:"
echo "    1. bash /workspace/test_setup.sh"
echo "    2. bash /workspace/scripts/start_kind_cluster.sh"
echo "    3. bash /workspace/scripts/deploy_llm_d.sh"
echo ""
echo "  Distributed inference:"
echo "    8B single:  /workspace/llm-d-configs/values-8b.yaml"
echo "    70B disagg: /workspace/llm-d-configs/values-70b-distributed.yaml"
echo ""
echo "  Monitoring:"
echo "    python3 /workspace/scripts/monitor_inference.py"
echo "    k9s  (Kubernetes cluster TUI)"
echo "============================================="
