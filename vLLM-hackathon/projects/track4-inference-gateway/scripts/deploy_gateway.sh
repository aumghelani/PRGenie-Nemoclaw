#!/bin/bash
# Deploy the llm-d Inference Gateway with the given Helm values file.
# Usage: bash deploy_gateway.sh helm-values/values-multi-model.yaml
set -euo pipefail

VALUES="${1:-helm-values/values-multi-model.yaml}"

if [ ! -f "$VALUES" ]; then
    echo "✗ Values file not found: $VALUES" >&2
    exit 1
fi

echo "============================================="
echo "  Deploying llm-d Inference Gateway"
echo "  Values: $VALUES"
echo "============================================="

# --- Ensure the llm-d namespace exists ---
kubectl get namespace llm-d >/dev/null 2>&1 || kubectl create namespace llm-d

# --- Ensure the llm-d repo is available ---
if [ ! -d /workspace/llm-d ]; then
    echo "[1/3] Cloning llm-d..."
    git clone --depth 1 https://github.com/llm-d/llm-d.git /workspace/llm-d
fi

# --- Install or upgrade ---
echo "[2/3] Installing / upgrading the gateway..."
helm upgrade --install llm-d /workspace/llm-d/charts/llm-d \
    --namespace llm-d \
    -f "$VALUES" \
    --wait --timeout 300s

# --- Verify ---
echo "[3/3] Verifying..."
kubectl get pods -n llm-d
echo ""
kubectl get svc -n llm-d
echo ""
echo "✓ Gateway ready. Test it with:"
echo "  kubectl port-forward -n llm-d svc/llm-d-gateway 8000:8000 &"
echo "  curl http://localhost:8000/v1/models"
echo ""
echo "Drive mixed traffic with:"
echo "  python3 scripts/send_mixed_traffic.py --multi-model"
